package main

deny contains msg if {
    input.kind == "Pod"
    some i
    container := input.spec.containers[i]
    not container.resources.requests
    msg := "Pod containers must specify resource requests"
}

deny contains msg if {
    input.kind == "Pod"
    some i
    container := input.spec.containers[i]
    not container.resources.limits
    msg := "Pod containers must specify resource limits"
}