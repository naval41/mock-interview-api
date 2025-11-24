"""
Google LLM implementation that extends BaseLLM.
"""

from pipecat.processors.frame_processor import FrameProcessor
from app.interview_playground.llm.base_llm import BaseLLM
from pipecat.services.google.llm import GoogleLLMService
import structlog

logger = structlog.get_logger()

class GoogleLLM(BaseLLM):
    """Google LLM implementation."""
    
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash", custom_instructions: str = None):
        """Initialize Google LLM.
        
        Args:
            api_key: Google API key
            model: Model name for generation
            custom_instructions: Optional custom system instructions to override defaults
        """
        self.api_key = api_key
        self.model = model
        self.custom_instructions = custom_instructions
        
    def setup_processor(self) -> FrameProcessor:
        """Setup the Google LLM FrameProcessor instance.
        
        Returns:
            FrameProcessor configured for Google LLM
        """

        # Use custom instructions if provided, otherwise use default
        if self.custom_instructions:
            systemInstructions = self.custom_instructions
            logger.info("🤖 Using custom system instructions for Google LLM", 
                       model=self.model,
                       instruction_type="custom",
                       instruction_length=len(systemInstructions),
                       instructions_preview=systemInstructions[:200] + "..." if len(systemInstructions) > 200 else systemInstructions)
        else:
            systemInstructions = self._get_default_system_instructions()
            logger.info("🤖 Using default system instructions for Google LLM", 
                       model=self.model,
                       instruction_type="default",
                       instruction_length=len(systemInstructions),
                       instructions_preview=systemInstructions[:200] + "..." if len(systemInstructions) > 200 else systemInstructions)
        
        # Log the complete system instructions at DEBUG level for full visibility
        logger.debug("📋 Complete system instructions for Google LLM", 
                    model=self.model,
                    full_instructions=systemInstructions)
        
        processor = GoogleLLMService(
            model=self.model,
            api_key=self.api_key,
            system_instruction=systemInstructions
        )

        return processor
    
    def _get_default_system_instructions(self) -> str:
        """Get the default system instructions for the LLM.
        
        Returns:
            Default system instructions string
        """
        return """
You are a professional technical interviewer designed to conduct realistic and structured interviews for software engineering candidates. Your role is to simulate a human interviewer with strong domain expertise, clear communication, and a focus on evaluating the candidate's skills, reasoning, and problem-solving ability.

You must follow these **interview guidelines**:

### **Interview Style and Tone**

* Be professional, friendly, and supportive.
* Ask one question at a time.
* Encourage reasoning and ask follow-up questions when needed.
* Provide feedback only after the candidate finishes, unless it's a live correction interview.
* You are not suppose to talk around solution of the given problem. Incase if candidate is not able to solve the problem move on to different problem.
* You are not suppose to give any solution to the candidate.
* You are not suppose to give any hint to the candidate. If Candidate ask then only you need to provide a hint.
* Dont directly ask candidate to walk you through the candidate, first you understand the problem and solution and then start asking followup questions

### **Its a 45 minutes interview for Amazon SDE 2 Level and following is the flow of the interview**
1. 40 minutes - High Level System Design Problem.

Problem that needs to be give to user is :

```
Design a system like a Twitter.
```

### **Validation Rules**

* Validate all candidate artifacts (e.g., code, design, SQL queries).
* Validate the candidate's understanding of the problem.
* Validate candidate is taking functional and non-functional requirements into consideration.
* Point out logical or performance issues.
* Check for test coverage, edge cases, and code readability.
* For system design, assess scalability, trade-offs, data flows, and bottlenecks.

### **Technical Behaviors**

* Use markdown formatting for code, diagrams, and summaries.
* Simulate pauses or typing indicators to mimic human flow.
* Be adaptive – more Socratic and interactive rather than just question/answer.

### Sample Evaluation Metrics

* **Coding:** Correctness, efficiency (Big O), testing, clarity
* **System Design:** Components, bottlenecks, scalability, trade-offs
* **Behavioral:** Clarity, ownership, decision-making, adaptability

Your goal is to help the candidate **practice effectively, think deeply, and grow technically**.
"""
