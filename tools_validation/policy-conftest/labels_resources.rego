deny[msg] {
    input.kind == "Pod"
    not input.metadata.labels["app"]
    msg = "Pod must have an 'app' label"
}

deny[msg] {
    input.kind == "Deployment"
    not input.metadata.labels["app"]
    msg = "Deployment must have an 'app' label"
}

# Validar que los recursos tengan una anotación 'example' en la metadata
deny[msg] {
    input.kind == "Pod"
    not input.metadata.annotations["example"]
    msg = "Pod must have an 'example' annotation"
}

deny[msg] {
    input.kind == "Deployment"
    not input.metadata.annotations["example"]
    msg = "Deployment must have an 'example' annotation"
}