package main

deny contains msg if {
    input.kind == "Deployment"
    input.spec.template.spec.containers[_].image == "latest"
    msg := "Containers must not use the 'latest' image tag"
}