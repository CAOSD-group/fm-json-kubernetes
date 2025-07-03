# Validar que los contenedores no se ejecuten como root
deny[msg] {
    input.kind == "Pod"
    input.spec.containers[_].securityContext.runAsUser == 0
    msg = "Containers must not run as root"
}

# Validar que el Pod tenga 'runAsNonRoot' configurado en su securityContext
deny[msg] {
    input.kind == "Pod"
    not input.spec.containers[_].securityContext.runAsNonRoot
    msg = "Containers must specify runAsNonRoot as true"
}