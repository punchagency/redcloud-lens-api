**1. Type:**

* **feat:** A new feature
* **fix:** A bug fix
* **docs:** Documentation only changes
* **style:** Changes that do not affect the meaning of the code (white-space, formatting, etc.)
* **refactor:** A code change that neither fixes a bug nor adds a feature
* **perf:** A code change that improves performance
* **test:** Adding missing or correcting existing tests
* **build:** Changes that affect the build system or external dependencies (example scopes may include: docker, npm)
* **ci:** Changes to our CI/CD pipelines
* **chore:** Other changes that don't fall into any of the above categories

**2. Scope (Optional):**

* Specify the area of the code that is affected by the change.
    * Example: `feat(api)` 

**3. Short Description:**

* A concise summary of the change (max 50 characters)
* Use the imperative mood (e.g., "Add user profile page", "Fix login issue")

**4. Body (Optional):**

* Provide more detailed information about the change.
* Wrap the body at 72 characters.

**5. Footer (Optional):**

* Issues and references:
    * "Closes #123" 
    * "Related to #456"
    * "See also #789"

**Example:**

```
feat(api): Add user registration endpoint

Allows new users to register for the application.
Includes basic validation and email verification.

Closes #123
```

**Key Considerations:**

* **Consistency:** Adhere to these conventions consistently within your team or project.
* **Conciseness:** Keep commit messages brief and to the point.
* **Clarity:** Use clear and concise language.
* **Meaningful Commits:** Each commit should represent a single, well-defined change.

**Benefits:**

* **Improved Code History:** Easier to understand the history of changes.
* **Better Collaboration:** Facilitates communication and collaboration among developers.
* **Easier Debugging:** Helps pinpoint the cause of issues more quickly.
* **Automated Tools:** Enables the use of tools that analyze commit history for various purposes.

By following these guidelines, you can create high-quality, informative, and maintainable git commit messages.
