package main

deny contains msg if {
    input.kind == "NetworkPolicy"
    not input.spec.podSelector
    msg := "NetworkPolicy must define a podSelector"
}

deny contains msg if {
    input.kind == "NetworkPolicy"
    not input.spec.ingress
    msg := "NetworkPolicy must define ingress rules"
}