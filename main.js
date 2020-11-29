load_graph_from_json();

function clamp(x, lo, hi) {
    return x < lo ? lo : x > hi ? hi : x;
}

function display_graph(graph, width=800, height=600) {
    let svg = d3.select("body").append("svg")
        .attr("viewBox", [0, 0, width, height]);
    
    let link = svg.selectAll(".link")
        .data(graph.links)
        .join("line")
        .classed("link", true);
    
    let node = svg.selectAll(".node")
        .data(graph.nodes)
        .enter().append("g")
            .attr("transform", (d) => "translate(" + d.x + "," + d.y + ")");
    
    node.append("circle")
        .attr("class", "node")
        .attr("r", 10);
    
    node.append("text")
        .attr("dx", 12)
        .attr("dy", ".35em")
        .text(d => d.name);

    let simulation = d3
        .forceSimulation()
        .nodes(graph.nodes)
        .force("charge", d3.forceManyBody().strength(-100))
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force("link", d3.forceLink(graph.links))
        .on("tick", tick);

    let drag = d3
        .drag()
        .on("start", dragstart)
        .on("drag", dragged);
    
    node.call(drag).on("click", click);
    
    function tick() {
        link
            .attr("x1", d => d.source.x)
            .attr("y1", d => d.source.y)
            .attr("x2", d => d.target.x)
            .attr("y2", d => d.target.y);
        node
            .attr("transform", d => "translate(" + d.x + ", " + d.y + ")");
    }
        
    function click(e, d) {
        delete d.fx;
        delete d.fy;
        d3.select(this).classed("fixed", false);
        simulation.alpha(1).restart();
    }
    
    function dragstart() {
        d3.select(this).classed("fixed", true);
    }
    
    function dragged(e, d) {
        d.fx = clamp(e.x, 0, width);
        d.fy = clamp(e.y, 0, height);
        simulation.alpha(1).restart();
    }
}

function build_graph(json) {
    let index_mapping = {}

    let graph = {
        nodes: [],
        links: []
    }

    function add_node(code) {
        let node = { name: code };
        index_mapping[node.name] = graph.nodes.push(node) - 1;
        return node;
    }

    let links = [];
    json.forEach(s => {
        let node = add_node(s.code);
        s.constraints.forEach(c => {
            if (c[0] === "SUBJECTS") {
                let [_, qty, opts, conc] = c;
                opts.forEach(o => {
                    links.push([node.name, o]);
                });
            }
        });
    });

    function get_index(s) {
        let i = index_mapping[s];
        if (i !== undefined) {
            return i;
        }
    
        add_node(s);
        return get_index(s);
    }

    links.forEach(l => {
        let [start, end] = l;

        graph.links.push({
            source: get_index(start),
            target: get_index(end) 
        });
    })

    return graph;
}

function load_graph_from_json(file="mast.json") {
    fetch(file)
        .then(resp => resp.json())
        .then(data => display_graph(build_graph(data)));
}
