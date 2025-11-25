search_default_knowledge_base_description = f"""
Retrieve public technical information from the **Default Knowledge Base**.
This method searches the global, system-wide knowledge base shared across all users.
It contains general technical materials such as manuals, troubleshooting guides,
or reference documents for domains like *Fanuc* or *Mitsubishi*.  
Every user has access to this knowledge base.

Args:
    query (str): The natural-language question or topic to search for.
    domain (Literal["fanuc", "mitsubishi"], optional): 
        The manufacturer or product domain context. Defaults to "fanuc".

Returns:
    str: A formatted summary string containing relevant results such as text,
            tables, or images. Returns an error message string if retrieval fails.

Example:
    >>> tool = SearchDefaultKnowledgeBaseTool(kb_ids=["kb_default"])
    >>> result = tool.invoke("Fanuc alarm 401 meaning", domain="fanuc")
    Alarm 401: Servo mismatch alarm.
    Possible causes:
        - Incorrect axis configuration.
        - Mismatched amplifier ID.
    Recommended actions:
        1. Verify configuration.
        2. Reset the amplifier.
"""

search_company_knowledge_base_description = """
Retrieve internal data from the **Company Knowledge Base**.
This method searches the company-wide knowledge base that stores
internal documents, standard operating procedures (SOPs), service reports,
or troubleshooting experiences shared among users of the same company.
Data in this collection is private to each company — users from other companies
cannot access it.

Args:
    query (str): The question or keyword describing what to search within the
        company-level knowledge base.

Returns:
    str: A formatted string combining internal documents, tables, and images
            related to the query. Returns an error message string if retrieval fails.

Example:
    >>> tool = SearchCompanyKnowledgeBaseTool(kb_ids=["kb_company_MB"])
    >>> result = tool.invoke("Quy trình xử lý sự cố servo không khởi động được")
    >>> print(result)
    Company SOP: Servo startup failure handling
    1. Verify power connection.
    2. Check encoder cable.
    3. Escalate to maintenance lead if unresolved.
"""

search_project_knowledge_base_description = """
Retrieve personal documents from the **Project Knowledge Base**.
This method searches files and notes uploaded by an individual user.
Each user’s project knowledge base is isolated and contains their own
private materials — such as experiment results, work logs, project documents,
or uploaded manuals.  
Only the owner can access their uploaded content.

Args:
    query (str): The question or keyword describing what to search
        in the user’s personal project files.

Returns:
    str: A formatted string summarizing matching personal documents,
            including text, tables, or images. Returns an error message
            if retrieval fails.

Example:
    >>> tool = SearchProjectKnowledgeBaseTool(kb_ids=["proj_user_123"])
    >>> result = tool.invoke("Final test report for my 2025 spindle project")
    >>> print(result)
    Report: Spindle Motor Test (2025)
    - Load: 95%
    - Temperature: 72°C
    - Duration: 3 hours
    Status: Passed.
"""

search_experience_knowledge_base_description = """
Search for repair experiences in the **Experience Knowledge Base**.
The Experience Knowledge Base stores real-world maintenance cases
and troubleshooting experiences contributed by factory technicians.
Each record typically describes how a machine failure was diagnosed
and resolved — including observed symptoms, root cause, and fix steps.

This method allows users to ask natural questions (in plain language)
and retrieve similar past cases from actual on-site repairs.

Args:
    query (str):
        The issue or question to search for. Examples:
        - "Robot does not move after emergency stop reset"
        - "Servo overcurrent when running at high speed"
        - "CNC spindle overheating after 2 minutes of operation"

Returns:
    str:
        A formatted string containing one or more relevant maintenance
        cases, each with its symptoms, root cause, and resolution steps.
        Returns an error message if retrieval fails.

Example:
    >>> tool = SearchExperienceKnowledgeBaseTool(kb_ids=["exp_factory_line3"])
    >>> result = tool.invoke(
    ...     "Fanuc robot not moving after E-stop release"
    ... )
    >>> print(result)
    Case ID: EXP-2025-042
    Symptoms: Robot does not move, lights remain green.
    Root cause: Teach pendant was still in HOLD mode.
    Resolution: Switch to AUTO mode and re-enable servo power.
    Severity: Low
    Time spent: 15 minutes
"""

filling_experience_ticket_description = """
Generate a pre-filled maintenance ticket (Experience Ticket) URL.
This tool automatically builds a link to the "New Corrective Action" page
with all relevant incident fields pre-filled based on information parsed
from the user–chatbot conversation.  
It helps technicians quickly log repair reports without retyping details.

Typical fields include:
    - Error title and code
    - Device model and serial number
    - Priority and severity
    - Observed symptoms
    - Root cause and resolution steps
    - Temporary workaround
    - Time spent and material cost

Args:
    error_title (str, optional): Short summary of the issue (e.g., "Spindle Overheat Alarm 250").
    error_code (str, optional): Error or alarm code, if available.
    device (str, optional): Affected machine or robot model.
    serial_number (str, optional): Serial number of the equipment.
    error_component (str, optional): Component where the issue occurred.
    priority (str, optional): Priority level ("HIGH", "MEDIUM", "LOW").
    severity (str, optional): Impact severity (e.g., "Line down", "Minor").
    occurred_at (str, optional): Time the issue occurred (ISO datetime or description).
    symptoms (str, optional): Observed symptoms or abnormal behavior.
    root_cause (str, optional): Identified root cause of the issue.
    steps_to_reproduce (str, optional): Steps to reproduce the failure.
    workaround (str, optional): Temporary workaround used to continue operation.
    resolution_steps (str, optional): Permanent corrective actions taken.
    time_spent_mins (int, optional): Time spent fixing the issue (in minutes).
    material_cost_used (float, optional): Cost of materials used for repair.

Returns:
    str:
        A full front-end URL pointing to the maintenance form page
        with all parameters pre-filled as query strings.

Example:
    >>> tool = FillingExperienceTicketTool()
    >>> url = tool.invoke(
    ...     error_title="Alarm 250 Spindle Overheat",
    ...     device="CNC Spindle Unit XZ-900",
    ...     severity="Line down",
    ...     symptoms="Spindle temperature >90°C after 2 minutes",
    ...     root_cause="Cooling fan blocked by dust",
    ...     resolution_steps="Clean fan and reapply thermal grease",
    ...     time_spent_mins=45,
    ...     material_cost_used=120.5
    ... )
    >>> print(url)
    https://ugate.ai/corrective-actions/new?errorTitle=Alarm+250+Spindle+Overheat&device=CNC+Spindle+Unit+XZ-900&...
"""

tavily_search_description = """
Search for information on the public Internet using Tavily (Web Search Tool).ư
This tool performs real-time web searches to retrieve up-to-date data
from online sources when the information is not available in any internal
knowledge base (Default, Company, Project, or Experience).

It is especially useful for:
    - Looking up manufacturer documentation
    - Finding community or forum discussions
    - Researching new or rare machine error codes
    - Getting recently published information

Args:
    query (str):
        The search query or problem description. Examples:
        - "Mitsubishi servo alarm 37 cause and fix"
        - "Fanuc SRVO-068 DTERR troubleshooting steps"
        - "meaning of alarm 401 on latest Fanuc controller"

Returns:
    str:
        A formatted summary string of the most relevant web results,
        including meanings, common causes, recommended fixes,
        and key reference links.  
        Returns an error message if the search fails.

Example:
    >>> tool = TavilyWebSearchTool()
    >>> result = tool.invoke("Mitsubishi servo alarm 37 meaning and fix")
    >>> print(result)
    Alarm 37: Excessive regenerative current.
    Common causes:
        - High inertia load deceleration
        - Faulty regenerative resistor
    Suggested fix:
        - Check resistor wiring
        - Reduce deceleration rate
    Sources:
        - mitsubishi-robotics.com
        - automationforum.net
"""

authen_check_description = """
Check whether a transaction serial number is authentic by validating it against
the official database of genuine product serial numbers.

Use this tool when the user wants to confirm if a product or transaction code
is real or counterfeit. Typical user requests include:
- "Check the authenticity of serial number m250000598"
- "Is this serial real: M200213739?"
- "Verify m250000599"
- "Is this code fake or genuine?"

What the tool does:
1. Look up the provided serial number in the database of authentic serials.
2. If a match is found, return AUTHENTIC along with product information.
3. If no match exists, return FAKE / COUNTERFEIT (0 records found).

Args:
    serial_number (str): The serial number to verify. It may be provided directly
                         or extracted from the user's message.
                         Examples:
                         - m250000598
                         - M200213739
                         - ABC-123-456

Returns:
    str: A formatted response indicating whether the serial number is authentic.
         If authentic, the result includes product details; otherwise, it clearly
         states that the serial is fake or counterfeit.
"""
