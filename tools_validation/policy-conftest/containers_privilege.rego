package main

deny contains msg if {
    input.kind == "Pod"
    some i
    container := input.spec.containers[i]
    container.securityContext.runAsUser == 0
    msg := "Containers must not run as root"
}

deny contains msg if {
    input.kind == "Pod"
    some i
    container := input.spec.containers[i]
    not container.securityContext.runAsNonRoot
    msg := "Containers must specify runAsNonRoot as true"
}