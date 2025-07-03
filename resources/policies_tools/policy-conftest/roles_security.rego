deny[msg] {
    input.kind == "RoleBinding"
    input.subjects[_].kind != "ServiceAccount"
    msg = "RoleBinding must reference ServiceAccount"
}

deny[msg] {
    input.kind == "Role"
    input.rules[_].verbs[_] == "all"
    msg = "Role should not allow all verbs"
}