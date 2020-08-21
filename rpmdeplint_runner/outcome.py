from enum import Enum


class TmtExitCodes(Enum):
    PASSED = 0
    FAILED = 1
    ERROR = 2
    SKIPPED = 3

    @classmethod
    def from_rpmdeplint(cls, return_code):
        return TmtExitCodes[return_code.name]


class RpmdeplintCodes(Enum):
    PASSED = 0
    ERROR = 2
    FAILED = 3

    @classmethod
    def from_rc(cls, return_code):
        if return_code == 1 or return_code > 3:
            # from CI perspective, incorrect usage or infra error is the same;
            # it's something CI maintainers need to fix, not users.
            # and unknown (undocumented) return code means unknown error
            return_code = 2
        return cls(return_code)
