package main

deny contains msg if {
    input.kind == "RoleBinding"
    some i
    subject := input.subjects[i]
    not subject.kind == "ServiceAccount"
    msg := "RoleBinding must reference ServiceAccount"
}

deny contains msg if {
    input.kind == "Role"
    some i
    rule := input.rules[i]
    rule.verbs[_] == "*"
    msg := "Role should not allow all verbs"
}