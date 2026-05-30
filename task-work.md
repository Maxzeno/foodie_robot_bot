I would like to reduce cost of calling the llm because i use custom tools and they take up alot of the input tokens i decides to reduce the tokens by performing a two way openai call first one with the user input i ask the llm to link exactly two function names that are related to the user input (i will pass in only the function names into the system prompt for the llm to know the functions)

after this i will then make another api call with only the two selected custom tools and then the llm can call any of the tools if needed

I want you to think about thing and tell me potential downsides, cost effectiveness, any potential better alternatives and why 

the logic for this in the api/services/ai folder

 Better Alternatives

  1. Prompt Caching (Best option)

  Use OpenAI's prompt caching - tool definitions cached, only pay once
  Savings: ~90% on repeated tool definition tokens

  2. Embedding-based pre-filtering

  Use embedding similarity (cheap) → filter to top 3-5 tools → single LLM call
  Cost: ~$0.0001 per embedding vs full LLM call

  3. Optimize tool descriptions

  Reduce verbose descriptions, use concise parameter schemas
  Often can cut tokens by 50-70% without losing clarity

  4. Use a smaller model for tool selection

  First call: gpt-4o-mini (cheaper) selects tools
  Second call: full model with selected tools
  Better accuracy than name-only, lower cost than full model twice

  5. Hierarchical tool organization

  Group tools by category (user-mgmt, orders, inventory)
  Select category first, then only load tools from that category

  My recommendation: Start with #1 (prompt caching) + #3 (optimize descriptions). This is the simplest      
  and most effective. Only add tool pre-selection if you still have cost issues after that.

  Would you like me to look at your current implementation in api/services/ai to give more specific
  recommendations?
