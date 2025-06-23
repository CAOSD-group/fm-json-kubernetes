package main

deny contains msg if {
    input.kind == "Pod"
    not input.metadata.labels.app
    msg := "Pod must have an 'app' label"
}

deny contains msg if {
    input.kind == "Deployment"
    not input.metadata.labels.app
    msg := "Deployment must have an 'app' label"
}

deny contains msg if {
    input.kind == "Pod"
    not input.metadata.annotations.example
    msg := "Pod must have an 'example' annotation"
}

deny contains msg if {
    input.kind == "Deployment"
    not input.metadata.annotations.example
    msg := "Deployment must have an 'example' annotation"
}