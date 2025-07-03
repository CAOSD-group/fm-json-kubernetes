package main

deny[msg] {
  input.kind == "Pod"
  container := input.spec.containers[_]
  not container.resources.requests.cpu
  msg := sprintf("Container '%s' is missing CPU request", [container.name])
}

deny[msg] {
  input.kind == "Pod"
  container := input.spec.containers[_]
  not container.resources.limits.memory
  msg := sprintf("Container '%s' is missing memory limit", [container.name])
}