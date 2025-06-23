package main

deny contains msg if {
    input.kind == "Pod"
    some i
    container := input.spec.containers[i]
    not container.livenessProbe
    msg := "Pod containers must have a livenessProbe"
}

deny contains msg if {
    input.kind == "Pod"
    some i
    container := input.spec.containers[i]
    not container.readinessProbe
    msg := "Pod containers must have a readinessProbe"
}