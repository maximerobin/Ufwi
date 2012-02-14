
def typenormalizer(value, context, expectedclass):
    if not isinstance(value, expectedclass):
        raise ValueError(
            "[%s] expected type <%s>, but <%s>" %
            (context, expectedclass, type(value))
        )

    return value

def specialproperty(
        normalizer,
        attrname,
        normalizer_args=(),
        normalizer_kwargs=None
        ):

    if normalizer_kwargs is None:
        normalizer_kwargs = {}

    real_attrname = '__%s' % attrname

    def setter(self, value):
        value = normalizer(
            value,
            "Setting attr %s" % attrname,
            *normalizer_args,
            **normalizer_kwargs
            )
        setattr(self, real_attrname, value)

    def getter(self):
        return getattr(self, real_attrname, '')

    setattr(setter, '__name__', '_set%s' % attrname)
    setattr(getter, '__name__', '_get%s' % attrname)

    return property(fset=setter, fget=getter)

def textlinenormalizer(value, context):
    if value is None:
        return u""

    if not isinstance(value, (str, unicode)):
        raise ValueError("[%s] Expected a string, got a '%s'" %
                (context, type(value))
                )
    return value.replace("\n", "")

def WORDnormalizer(value, context):
    if value is None:
        return u""

    if not isinstance(value, (str, unicode)):
        raise ValueError("[%s] Expected a string, got a '%s'" %
                (context, type(value))
                )

    #---  normalization ---
    value = value.strip()
    #concatenation
    value = "".join(value.split())
    #capitalization
    return value.upper()

def typedproperty(expectedclass, attrname):
    """
    expectedclass: a class or a tuple of classes
    attrname: the attribute name in your target class
    """
    return specialproperty(typenormalizer, attrname, (expectedclass,))

def textlineproperty(attrname):
    """
    attrname: the attribute name in your target class

    Checks that a single line of text was input. Otherwise, suppresses "\n"s
    """
    return specialproperty(textlinenormalizer, attrname)

def WORDproperty(attrname):
    """
    attrname: the attribute name in your target class

    Checks that a single capitalized word was input.
    Normalization:
     * capitalizes
     * concatenates words
    """
    return specialproperty(WORDnormalizer, attrname)

