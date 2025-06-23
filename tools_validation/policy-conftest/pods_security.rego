package main

deny contains msg if {
    input.kind == "Pod"
    input.spec.securityContext.runAsUser != 1000
    msg := "Pod must run as non-root user with ID 1000"
}