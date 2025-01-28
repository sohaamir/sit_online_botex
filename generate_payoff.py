import matplotlib.pyplot as plt

def calculate_bonus_payoff(score, divider):
    if score <= 0:
        return 0
    else:
        return round(score / divider, 2)

# Generate data for the graph
scores = range(0, 4801, 100)  # From 0 to 4800 in steps of 100
dividers = [500, 625, 750, 825, 950]
colors = ['red', 'green', 'blue', 'purple', 'orange']

# Create the graph
plt.figure(figsize=(12, 8))

for divider, color in zip(dividers, colors):
    bonus_payoffs = [calculate_bonus_payoff(score, divider) for score in scores]
    plt.plot(scores, bonus_payoffs, label=f'Divider: {divider}', color=color)

plt.title('Bonus Payoff vs Score for Different Dividers')
plt.xlabel('Score')
plt.ylabel('Bonus Payoff (£)')
plt.grid(True)
plt.legend()

# Add reference line for maximum bonus (assuming 4800 is max score)
max_bonus = max(calculate_bonus_payoff(4800, divider) for divider in dividers)
plt.axhline(y=max_bonus, color='black', linestyle='--', label=f'Max Bonus: £{max_bonus:.2f}')

plt.legend()

if __name__ == "__main__":
    plt.show()  # This will display the graph

    # Optional: User input loop for calculating payoff
    while True:
        user_input = input("Enter a score and divider (e.g., '2400 750') or 'q' to quit: ").strip().lower()
        if user_input == 'q':
            print("Exiting...")
            break
        try:
            score, divider = map(float, user_input.split())
            bonus_payoff = calculate_bonus_payoff(score, divider)
            total_payoff = 10 + bonus_payoff
            print(f"For a score of {score} and divider {divider}:")
            print(f"Bonus payoff: £{bonus_payoff:.2f}")
            print(f"Total payoff: £{total_payoff:.2f}")
        except ValueError:
            print("Please enter valid numbers or 'q' to quit.")
        except KeyboardInterrupt:
            print("\nExiting...")
            break