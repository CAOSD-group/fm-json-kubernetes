deny[msg] {
    input.kind == "NetworkPolicy"
    not input.spec.podSelector
    msg = "NetworkPolicy must define a podSelector"
}

deny[msg] {
    input.kind == "NetworkPolicy"
    not input.spec.ingress
    msg = "NetworkPolicy must define ingress rules"
}