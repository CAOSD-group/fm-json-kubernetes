deny[msg] {
    input.kind == "Pod"
    not input.spec.tolerations
    msg = "Pod must define tolerations"
}