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

function nodes_to_d3_graph(nodes) {
    let graph = {
        nodes: nodes.list,
        links: []
    };

    nodes.list.forEach(n => {
        n.neighbours.forEach(o => {
            graph.links.push({
                source: nodes.list.indexOf(n),
                target: nodes.list.indexOf(o) 
            })
        });
    });

    return graph;
}

function accessible_from(nodes, root='MAST20009') {
    let root_node = nodes.get(root);    
    root_node.visited = true;
    let next = [root_node];
    let cur;
    while (next.length) {
        cur = next;
        next = [];

        cur.forEach(n => {
            n.neighbours.forEach(o => {
                if (!o.visited) {
                    next.push(o);
                }
                o.visited = true;
            });
        });
    }

    let to_remove = [];
    nodes.list.forEach(n => {
        if (!n.visited) {
            to_remove.push(n);
        }
        delete n.visited;
    });

    to_remove.forEach(n => {
        nodes.list.splice(nodes.list.indexOf(n), 1);
        delete nodes[n.name];
    })

    return nodes;
}

function build_nodes(json) {
    let nodes = {list: []};
    nodes.get = (n) => {
        if (n in nodes) {
            return nodes[n];
        }

        let node = {neighbours: [], name: n};

        nodes[n] = node;
        nodes.list.push(node);
        return node;
    };

    json.forEach(s => {
        s.constraints.forEach(c => {
            let node = nodes.get(s.code);
            if (c[0] === "SUBJECTS") {
                let [_, qty, opts, conc] = c;
                opts.forEach(o => {
                    node.neighbours.push(nodes.get(o));
                });
            }
        });
    });

    return nodes;
}

function load_graph_from_json(file="mast.json") {
    fetch(file)
        .then(resp => resp.json())
        .then(data => display_graph(nodes_to_d3_graph(accessible_from(build_nodes(data)))));
}
