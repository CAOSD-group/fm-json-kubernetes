# Validar que los contenedores tengan configurados los recursos 'requests' y 'limits'
deny[msg] {
    input.kind == "Pod"
    not input.spec.containers[_].resources.requests
    msg = "Pod containers must specify resource requests"
}

deny[msg] {
    input.kind == "Pod"
    not input.spec.containers[_].resources.limits
    msg = "Pod containers must specify resource limits"
}