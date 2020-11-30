load_graph_from_json();

function clamp(x, lo, hi) {
    return x < lo ? lo : x > hi ? hi : x;
}

function display_graph(graph, width=800, height=600) {
    let svg = d3.select("body").append("svg")
        .attr("viewBox", [0, 0, width, height]);
    
    let defs = svg.append('defs');
    
    defs.append('marker')
        .attrs({
            'id': 'arrowhead',
            'viewBox': '-0 -5 10 10',
            'refX': 22,
            'refY': 0,
            'orient': 'auto',
            'markerWidth': 5,
            'markerHeight': 5
        })
        .append('svg:path')
        .attr('d', 'M 0, -5 L 10, 0 L 0, 5')
        .attr('fill', '#999')
        .style('stroke', 'none');

    let link = svg.selectAll(".link")
        .data(graph.links)
        .join("line")
        .classed("link", true)
        .attr('marker-end', 'url(#arrowhead)');
    
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
        .force("charge", d3.forceManyBody().strength(-60))
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

function scrub_unvisited(nodes) {
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
    });

    return nodes;
}

function accessible_from(nodes, root_node) {
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

    return scrub_unvisited(nodes);
}

function build_tree(nodes, root = 'MAST30028') {
    let ensure_children = p => {
        if (p.children === undefined) {
            p.children = [];
        }
    }

    let add_child = (p, c) => {
        ensure_children(p);
        p.children.push(c);
    }

    root = nodes.get(root);
    root.visited = true;

    let next = [ root ];
    let cur;
    while (next.length) {
        cur = next;
        next = [];
        cur.forEach(n => {
            n.neighbours.forEach(o => {
                if (!o.visited) {
                    o.visited = true;
                    next.push(o);
                    add_child(n, o); 
                }
            })
        });
    }

    scrub_unvisited(nodes);

    nodes.list.forEach(n => {
        ensure_children(n);
        n.neighbours = n.children;
        delete n.children;
    });

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
                if (qty >= 0) {
                    opts.forEach(o => {
                        node.neighbours.push(nodes.get(o));
                    });    
                }
            }
        });
    });

    return nodes;
}

function load_graph_from_json(file="mast.json") {
    fetch(file)
        .then(resp => resp.json())
        .then(data => display_graph(nodes_to_d3_graph(build_tree(build_nodes(data)))));
}
