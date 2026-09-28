# Working in this repo

1. **Never commit secrets.** API keys, tokens, passwords and `.env` files stay on your machine. Code reads them from environment variables (for example `SUPABASE_ANON_KEY`). A secret scan runs on every push and pull request.
2. **Never commit customer data.** No real names, phone numbers, emails, credit details or exports. Use `example.com` addresses and `555` phone numbers in samples.
3. **Branch, then open a pull request.** Don't push to `main`. The owner reviews every change.
4. **Stay in your folder.** Each top-level folder is its own project with its own README and tooling.

If you think a secret or customer record got committed, tell the owner right away. Don't try to fix the history yourself.
