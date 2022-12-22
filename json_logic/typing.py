# Credits: https://github.com/python/typing/issues/182
Primitive = str | int | float | bool | None
Object = dict[str, "JSON"]
Array = list["JSON"]
JSON = Primitive | list["JSON"] | dict[str, "JSON"]
