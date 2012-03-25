#coding: utf-8

"""
Copyright (C) 2009-2011 EdenWall Technologies

This file is part of NuFirewall. 
 
 NuFirewall is free software: you can redistribute it and/or modify 
 it under the terms of the GNU General Public License as published by 
 the Free Software Foundation, version 3 of the License. 
 
 NuFirewall is distributed in the hope that it will be useful, 
 but WITHOUT ANY WARRANTY; without even the implied warranty of 
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the 
 GNU General Public License for more details. 
 
 You should have received a copy of the GNU General Public License 
 along with NuFirewall.  If not, see <http://www.gnu.org/licenses/>

gen_recursor is a recursor generator.

It recurses on identically named methods before calling the decorated
method itself.
Every method's result is parsed for conformity by a method you supply.
Every method's result is parsed to decide if the recursion should be
continued or not by a method you supply.
Recursion is only performed on the direct parent classes, not on grandparents,
therefore it is not a problem if many inherited methods are decorated.

usage:
a) create the result validation method that eventually raises significant
   exceptions if something is wrong.
b) create the result analysis method: True if the loop must be stopped
   and the current result returned, False otherwise.
c) finally create the decorator method with gen_recursor as a helper.

Example:


def _valid(parent_result, parent_method):
    if parent_result is None:
        raise TypeError(
            "Wrong result type produced by method %s - '%s'" %
            (parent_method, repr(parent_result))
        )

def _return_early(parent_result):
    should_stop = parent_result[42] % 3 == 0
    if should_stop:
        #Means the decorated method will return the parent_result we
        #just evaluated
        return True
    return False

callParent_isValidWithMsg = gen_recursor(
    'callParent_methodname',
    'methodname',
    _valid,
    _return_early,
    \"""
    This decorator will call parent's methodname.

    It returns early if a result[42] dividable by 3 is found.
    Checks that are done:
    -cannot decorate anything but methodname methods
    -returns have to be of type indexable, and not None
    \"""
    )
"""

from functools import wraps

def gen_recursor(
    decorator_name,
    function_name,
    parent_result_validator,
    early_result_evaluator,
    docstring):
    """
    Generate decorator that will recurse over parents samely named methods.

    Only recurses one degree.
    parent_result_validator should raise TypeError upon unexpected results.
    The iteration is stopped when early_result_evaluator says True upon a
    given result.
    The docstring will be set on the generated decorator.
    The name of the decorated function is checked by the generated decorator
    (ValueError).
    """

    if not callable(parent_result_validator):
        raise TypeError(
            "parent_result_validator aka %s is not callable" % \
            parent_result_validator
            )

    if not callable(early_result_evaluator):
        raise TypeError(
            "early_result_evaluator aka %s is not callable" % \
            parent_result_validator
            )

    def recursor(method):
        """
        This docstring should be replaced by the one specified by the
        'docstring' argument
        """
        if method.__name__ != function_name:
            raise ValueError(
                'Cannot decorate another method than %s. Used on %s' % \
                (function_name, method.__name__)
                )

        #The decorated method is being replaced by parent_caller
        #that is itself decorated by wraps in order to copy
        #all useful attributes
        @wraps(method)
        def parent_caller(self, *args, **kw):
            """
            This docstring should be replaced by the decorated method's
            """
            parents = self.__class__.__bases__
            for parent in parents:
                parent_method = getattr(parent, function_name, None)
                if self.__class__ is parent:
                    #skip current class in recursion
                    continue
                if parent_method is None:
                    #skip if the method is not defined at this level
                    continue
                if parent_method == getattr(self.__class__, function_name):
                    #Skip if method is the one inherited
                    #For instance do not recurse on A when invoked
                    #on an object of type B in the following example:
                    #class A(object):
                    #    @decorator_name
                    #    def plop(self):
                    #        pass
                    #class B(object):
                    #    pass
                    #
                    continue
                #Ideally we would know the class in which 'method' is being
                #declared instead of the above tests.

                parent_result = parent_method(self, *args, **kw)
                parent_result_validator(parent_result, parent_method)
                if early_result_evaluator(parent_result):
                    #early return
                    return parent_result

            return method(self, *args, **kw)

        return parent_caller

    recursor.__name__ = decorator_name
    recursor.__doc__ = docstring

    return recursor

