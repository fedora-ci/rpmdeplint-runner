from rpmdeplint_runner.outcome import TmtExitCodes, RpmdeplintCodes


def test_tmt_from_rpmdeplint():
    rpmdeplint_passed = RpmdeplintCodes.from_rc(0)
    rpmdeplint_error = RpmdeplintCodes.from_rc(1)
    rpmdeplint_usage_error = RpmdeplintCodes.from_rc(2)
    rpmdeplint_unknown_error = RpmdeplintCodes.from_rc(73)
    rpmdeplint_failed = RpmdeplintCodes.from_rc(3)

    tmt_passed = TmtExitCodes.from_rpmdeplint(rpmdeplint_passed)
    tmt_error = TmtExitCodes.from_rpmdeplint(rpmdeplint_error)
    tmt_error_usage = TmtExitCodes.from_rpmdeplint(rpmdeplint_usage_error)
    tmt_error_unknown = TmtExitCodes.from_rpmdeplint(rpmdeplint_unknown_error)
    tmt_failed = TmtExitCodes.from_rpmdeplint(rpmdeplint_failed)

    assert tmt_passed.value == 0
    assert tmt_error.value == 2
    assert tmt_error_usage.value == 2
    assert tmt_error_usage.value == 2
    assert tmt_failed.value == 1
    assert tmt_error_unknown.value == 2
