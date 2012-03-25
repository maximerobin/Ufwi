from apply_rules import RunTests

class TestApplyRules(object):

    def test_apply_rules(self):
        assert RunTests().main()
