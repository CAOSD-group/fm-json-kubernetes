package main

deny contains msg if {
    input.kind == "PersistentVolumeClaim"
    not input.spec.storageClassName
    msg := "PersistentVolumeClaim must specify a storageClassName"
}