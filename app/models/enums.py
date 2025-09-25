from enum import Enum


class OrderStatus(str, Enum):
    CREATED = "CREATED"
    PAID = "PAID"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class PaymentMethod(str, Enum):
    CARD = "CARD"
    UPI = "UPI"
    NETBANKING = "NETBANKING"
    WALLET = "WALLET"
    RAZORPAY = "RAZORPAY"


class CandidateInterviewStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class InterviewLevel(str, Enum):
    ENTRY = "ENTRY"
    MID = "MID"
    SENIOR = "SENIOR"


class CodeLanguage(str, Enum):
    JAVASCRIPT = "JAVASCRIPT"
    TYPESCRIPT = "TYPESCRIPT"
    PYTHON = "PYTHON"
    JAVA = "JAVA"
    GO = "GO"
    CPP = "CPP"
    CSHARP = "CSHARP"
    RUBY = "RUBY"
    PHP = "PHP"
    SQL = "SQL"


class TranscriptSender(str, Enum):
    INTERVIEWER = "INTERVIEWER"
    CANDIDATE = "CANDIDATE"


class WorkflowStepType(str, Enum):
    INTRO = "INTRO"
    CODING = "CODING"
    SYSTEM_DESIGN = "SYSTEM_DESIGN"
    BEHAVIORAL = "BEHAVIORAL"
    QNA = "QNA"
    WRAP_UP = "WRAP_UP"


class Recommendation(str, Enum):
    STRONG_HIRE = "STRONG_HIRE"
    HIRE = "HIRE"
    LEANING_HIRE = "LEANING_HIRE"
    NO_HIRE = "NO_HIRE"
    STRONG_NO_HIRE = "STRONG_NO_HIRE"


class QuestionType(str, Enum):
    CODING = "CODING"
    SYSTEM_DESIGN = "SYSTEM_DESIGN"
    BEHAVIORAL = "BEHAVIORAL"
    GENERAL = "GENERAL"


class SessionStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class InterviewDifficulty(str, Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"

class ToolName(str, Enum):
    BASE = "BASE"
    CODE_EDITOR = "CODE_EDITOR"
    DESIGN_EDITOR = "DESIGN_EDITOR"

class EventType(str, Enum):
    SYSTEM = "SYSTEM"
    INTERVIEW = "INTERVIEW"


class ToolEvent(str, Enum):
    CODE_CONTENT = "CodeContent"
    DESIGN_CONTENT = "DesignContent"