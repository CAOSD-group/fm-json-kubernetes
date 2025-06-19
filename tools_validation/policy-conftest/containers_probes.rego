# Validar que los contenedores tengan un 'livenessProbe'
deny[msg] {
    input.kind == "Pod"
    not input.spec.containers[_].livenessProbe
    msg = "Pod containers must have a livenessProbe"
}

# Validar que los contenedores tengan un 'readinessProbe'
deny[msg] {
    input.kind == "Pod"
    not input.spec.containers[_].readinessProbe
    msg = "Pod containers must have a readinessProbe"
}