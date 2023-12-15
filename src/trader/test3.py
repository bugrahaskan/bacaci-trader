import asyncio

async def wait_for_condition(condition_event):
    print("Waiting for the condition to be True...")
    await condition_event.wait()
    print("Condition is now True!")

async def set_condition_after_delay(condition_event):
    await asyncio.sleep(2)  # Simulate some asynchronous operation
    print("Setting the condition to True...")
    condition_event.set()

async def main():
    condition = asyncio.Event()

    # Create tasks
    wait_task = asyncio.create_task(wait_for_condition(condition))
    set_condition_task = asyncio.create_task(set_condition_after_delay(condition))

    # Wait for both tasks to complete
    await asyncio.gather(wait_task, set_condition_task)

# Run the main function
asyncio.run(main())
