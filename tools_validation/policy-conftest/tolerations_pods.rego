package main

deny contains msg if {
    input.kind == "Pod"
    not input.spec.tolerations
    msg := "Pod must define tolerations"
}