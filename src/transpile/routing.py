from qiskit import transpile

def compile_k1(circuit, coupling_map, cfg):
    return transpile(
        circuit,
        coupling_map=coupling_map,
        basis_gates=list(cfg.routing.basis_gates),
        optimization_level=cfg.routing.optimization_level,
        layout_method=cfg.routing.layout_method,
        routing_method=cfg.routing.routing_method,
        seed_transpiler=cfg.rep.seed_transpiler,
    )
