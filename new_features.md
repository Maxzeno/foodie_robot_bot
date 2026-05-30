I am building a food recommendation Whatsapp bot that recommends two meals for morning, afternoon and evening based on the users health goals, preferences fitness goals etc and the can order from us if they want (that's how we make money we add some money on top then order the food for them)

I like the current implementation i have and i don't want you to overwrite or update it 

just list out tools i need to add to complete the project so users can use it and i can push the out and start making 
just list it out only for now i preferrer you write it to a md file

- Place order (this includes quantity/number of plates)
- Get order status by id or the latest order status
- Get order history please paginate like 5 at a time but allow users to fetch more when needed
- Tool to contact customer support
- Search for meal by name but return 5 max
- Get meal details
- Get user profile. include allergies, preferred cusine, average budget, health restrictions, fitness goal
- Get meals the user liked or hated
- Update their average budget (currency depends on the city the users last added delivery address is in - the currency is on the city and user fall under a city)
- Get payment status for latest created order - because after users pay they are likely to send a message i have paid so it's go to be able to tell me processing or payment confirmed and also we have another webhook that messages them message when the payment is confirmed
- Review if you liked the meal you just had that was ordered from us - can like hate or neutral


Please focus and only add this tool calls in the api/services/ai/tool_handlers folder don't touch my older tools or functions you can also update the tools_definitions files and the orchestrator file