from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from pydantic import BaseModel, ValidationError
from typing import Any, Dict, Type
import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY= os.getenv("OPENAI_API_KEY")
MODEL_API_KEYS = {
    "ChatOpenAI": OPENAI_API_KEY
}


class LLMHandler:
    def __init__(self, llm_type='ChatOpenAI', model_config=None, task_config=None):
        """
        Initialize the LLMHandler with a specific LLM type (Chat-based), model configuration, and task configuration.
        Args:
            llm_type (str): Type of the LLM to use (e.g., ChatOpenAI).
            model_config (dict): Configuration options for the selected LLM.
            task_config (dict): Configuration for task-specific behavior, such as prompts and data types.
        """
        self.llm_type = llm_type
        self.model_config = model_config or {}
        self.task_config = task_config or {}
        self.llm = self.initialize_llm()

    def initialize_llm(self):
        """
        Initializes the LLM based on the chosen type and configuration.
        """
        if "api_key" not in self.model_config:
            self.model_config["api_key"]= MODEL_API_KEYS[self.llm_type]

        if self.llm_type == 'ChatOpenAI':
            return ChatOpenAI(**self.model_config)
        else:
            raise ValueError(f"Unsupported LLM type: {self.llm_type}")

    def set_task_config(self, task_name: str, prompt_template: str, input_model: Type[BaseModel], output_model: Type[BaseModel], **kwargs):
        """
        Sets the configuration for a specific task, including the prompt template, input/output models, and other parameters.
        Args:
            task_name (str): The name of the task.
            prompt_template (str): The prompt template for the task.
            input_model (Type[BaseModel]): Pydantic model for input data validation.
            output_model (Type[BaseModel]): Pydantic model for output data validation.
            **kwargs: Any additional task-specific parameters.
        """
        self.task_config[task_name] = {
            'prompt_template': prompt_template,
            'input_model': input_model,
            'output_model': output_model,
            **kwargs
        }

    def generate_response(self, task_name: str, conversation_history: list = None, **input_data: Dict[str, Any]) -> str:
        """
        Generates a response for the given task using the configured LLM, ensuring input/output typing.
        Args:
            task_name (str): The name of the task for which a response should be generated.
            conversation_history (list): List of previous messages in the conversation (if any).
            **input_data: Data to be fed into the LLM for generating the response.
        """
        task_details = self.task_config.get(task_name)
        if not task_details:
            raise ValueError(f"Task '{task_name}' is not configured.")
        
        input_model = task_details.get('input_model')
        output_model = task_details.get('output_model')
        prompt_template = task_details.get('prompt_template')
        
        if not prompt_template:
            raise ValueError(f"Prompt template for task '{task_name}' is not defined.")

        # Validate input data using Pydantic model
        try:
            validated_input = input_model(**input_data)
        except ValidationError as e:
            raise ValueError(f"Invalid input data for task '{task_name}': {e}")

        # Construct the prompt using the input data
        prompt = PromptTemplate(template=prompt_template, input_variables=input_data.keys())
        formatted_prompt = prompt.format(**input_data)

        # Create messages for chat-based models
        messages = [SystemMessage(content="You are a helpful assistant.")]
        if conversation_history:
            messages.extend(conversation_history)
        
        messages.append(HumanMessage(content=formatted_prompt))

        # Get response from the LLM (ChatOpenAI)
        structured_llm = self.llm.with_structured_output(output_model)
        response = structured_llm.invoke(messages)

        # Validate the output using the output model
        # try:
        #     validated_output = output_model(**response)
        # except ValidationError as e:
        #     raise ValueError(f"Invalid output data from task '{task_name}': {e}")

        # Return the response text (or process as needed)
        return response
