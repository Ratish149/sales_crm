import os
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv

from .agent import GeminiAgent
from .structure_scanner import (
    analyze_project_resources,
    generate_file_tree,
    get_project_structure_summary,
)
from .tools import (
    apply_changes,
    apply_multiple_changes,
    delete_file,
    fetch_web_page,
    generate_design_inspiration,
    list_files,
    manage_dependencies,
    read_file,
    replace_in_file,
    search_files,
    web_search,
    write_file,
)

load_dotenv()


TOOL_FUNCTIONS = {
    "list_files": list_files,
    "read_file": read_file,
    "apply_multiple_changes": apply_multiple_changes,
    "apply_changes": apply_changes,
    "write_file": write_file,
    "delete_file": delete_file,
    "search_files": search_files,
    "replace_in_file": replace_in_file,
    "web_search": web_search,
    "fetch_web_page": fetch_web_page,
    "generate_design_inspiration": generate_design_inspiration,
    "manage_dependencies": manage_dependencies,
}


def execute_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool by name."""
    if name not in TOOL_FUNCTIONS:
        return {"status": "error", "message": f"Unknown tool: {name}"}

    try:
        func = TOOL_FUNCTIONS[name]
        result = func(**arguments)
        return result
    except Exception as e:
        return {"status": "error", "message": f"Tool execution failed: {str(e)}"}


def orchestrate_agent(
    user_prompt: str,
    project_root: str,
    max_iterations: int = 5,
    webhook_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Orchestrates the AI agent with proper Next.js 14 structure handling.
    """
    print(f"DEBUG Orchestrator: func called with webhook_url={webhook_url}")
    try:
        if not os.path.exists(project_root):
            return {
                "status": "error",
                "message": f"Project root not found: {project_root}",
            }

        original_cwd = os.getcwd()
        os.chdir(project_root)

        # 1. SCAN PROJECT STRUCTURE
        print("\n" + "=" * 80)
        print("🔍 SCANNING PROJECT STRUCTURE")
        print("=" * 80)
        try:
            project_summary = get_project_structure_summary(project_root)

            # Analyze resources
            resources_summary = analyze_project_resources(project_root)

            print(f"✅ Project scanned. Root: {project_root}")
        except Exception as e:
            print(f"⚠️ Structure scan failed: {e}")
            project_summary = f"Project Root: {project_root}"
            resources_summary = "Resources analysis failed."

        # 2. CONSTRUCT ENHANCED SYSTEM PROMPT
        system_prompt = f"""
## ROLE
You are a World-Class Full-Stack Next.js 14 Developer and Senior UI Designer specializing in high-conversion e-commerce and SaaS applications. Your goal is to build modern, pixel-perfect UI components that seamlessly integrate with the existing project architecture.

## PROJECT CONTEXT & STRUCTURE
{project_summary}

## VISUAL DESIGN STYLE
- **Aesthetic**: Clean, minimal, modern, and professional.
- **Colors**: Use PRIMARY and SECONDARY colors only.
- **Styling**: No shadows, no borders.
- **Layout**: Proper spacing, strong typography hierarchy, block-based layout.
- **Readability**: Logic and design should be easy to read and intuitive.
- **Tech Stack**: Output reusable, responsive components using Tailwind CSS.

{resources_summary}

## USER REQUEST
"{user_prompt}"

## CRITICAL NEXT.JS 14 ARCHITECTURE RULES

### 0. ICON USAGE PROTOCOL (STRICT)
- **Primary Source**: ALWAYS use `lucide-react` for icons.
- **Fallback**: If an icon is missing in lucide, use an **Inline SVG**.
- **FORBIDDEN**: Do NOT install or use `react-icons`, `@heroicons/react`, `font-awesome`, or any other icon package.
- **Import Pattern**: `import {{ IconName }} from "lucide-react";`

### 0.1 QUERY PROVIDER IMPORT RULE (STRICT)
- **Correct Import**: `import {{ QueryProvider }} from "@/components/providers/query-provider";`
- **FORBIDDEN**: Do NOT import from `@/contexts/QueryProvider` or any other path.
- **READ-ONLY**: This file exists. DO NOT modify it. DO NOT generate code for it.

### 0.2 COMPONENT IMPORT RULES (STRICT)
- **ImageWithFallback**: `import ImageWithFallback from "@/components/common/ImageWithFallback";` (PascalCase filname)
- **CRITICAL**: The `ImageWithFallback` component IS ALREADY AVAILABLE. DO NOT CREATE IT. DO NOT MODIFY IT. DO NOT create `image-with-fallback.tsx` or `ImageWithFallback.tsx`. STRICTLY USE THE EXISTING ONE.
- **Forbidden**: Do NOT import from `image-with-fallback` (kebab-case).

### 1. "use client" DIRECTIVE REQUIREMENTS
**MANDATORY**: Add `"use client"` at the TOP of ANY file that:
- Imports React hooks (`useState`, `useEffect`, `useContext`, etc.)
- Imports custom hooks from `@/hooks/` (e.g., `useProduct`, `useCart`)
- Uses browser APIs (`window`, `document`, `localStorage`)
- Uses event handlers (`onClick`, `onChange`, `onSubmit`)
- Uses any client-side interactivity

**Example of CORRECT client component:**
```typescript
"use client";

import {{ useState }} from "react";
import {{ useProduct }} from "@/hooks/use-product";
import {{ Button }} from "@/components/ui/button";

export default function ProductList() {{
  const {{ data, isLoading }} = useProduct();
  const [filter, setFilter] = useState("");
  
  return (
    <div>
      <Button onClick={{() => setFilter("active")}}>Filter</Button>
      {{/* Component JSX */}}
    </div>
  );
}}
```

### 2. PAGE STRUCTURE RULES

#### A. Creating New Pages
When the user requests a NEW PAGE (e.g., "create about us page", "make FAQ page"):

**Step 1**: Create the page at `src/app/[page-name]/page.tsx`
- Use kebab-case for folder names: `about-us`, `faq`, `contact-us`
- **DEFAULT**: Do NOT add `"use client"` unless the page file ITSELF extracts params or uses hooks. Prefer Server Components.

**Step 2**: Create the corresponding component at `src/components/[page-name]/[page-name].tsx`
- This component contains the actual page content
- Add `"use client"` if it uses hooks

**Step 3**: Import the component in the page file

**Example Structure:**
```
src/
├── app/
│   ├── about-us/
│   │   └── page.tsx          # Page wrapper with "use client" if needed
│   ├── faq/
│   │   └── page.tsx          # Page wrapper with "use client" if needed
│   └── page.tsx              # Main homepage
├── components/
│   ├── about-us/
│   │   └── about-us.tsx      # AboutUs component with "use client" if needed
│   └── faq/
│       └── faq.tsx           # FAQ component with "use client" if needed
```

#### B. Page Template Examples

**Full Page (e.g., About Us, FAQ):**
```typescript
// FILE: src/app/about-us/page.tsx
// Note: No "use client" here - it's a Server Component that renders a Client Component
import AboutUs from "@/components/about-us/about-us";

export default function AboutUsPage() {{
  return <AboutUs />;
}}
```

```typescript
// FILE: src/components/about-us/about-us.tsx
"use client";

import {{ useCompany }} from "@/hooks/use-company";
import {{ Button }} from "@/components/ui/button";

export default function AboutUs() {{
  const {{ data: companyInfo }} = useCompany();
  
  return (
    <section className="py-24">
      <div className="container mx-auto px-4">
        <h1 className="text-5xl font-bold">About Us</h1>
        {{/* Component content */}}
      </div>
    </section>
  );
}}
```

**Section Component (to be added to main page):**
```typescript
// FILE: src/components/faq-section/faq-section.tsx
"use client";

import {{ useState }} from "react";
import {{ useFAQ }} from "@/hooks/use-faq";
import {{ Accordion }} from "@/components/ui/accordion";

export default function FAQSection() {{
  const {{ data: faqs }} = useFAQ();
  const [openItem, setOpenItem] = useState<string | null>(null);
  
  return (
    <section id="faq" className="py-24 bg-gray-50">
      <div className="container mx-auto px-4">
        <h2 className="text-4xl font-bold text-center mb-12">
          Frequently Asked Questions
        </h2>
        {{/* FAQ content */}}
      </div>
    </section>
  );
}}
```

### 3. WHEN TO CREATE PAGES vs SECTIONS

**Create Full Page (app/[name]/page.tsx)** when user says:
- "Create [name] page"
- "Make a [name] page"
- "Build the [name] page"
- Examples: About Us, Contact, FAQ Page, Products Page

**Create Section Component** when user says:
- "Add [name] section"
- "Create [name] section for homepage"
- "Make a [name] component"
- Examples: Hero section, Features section, Testimonials section

**IMPORTANT**: For sections that should appear on the main page, you must:
1. Create the section component
2. Update `src/app/page.tsx` to import and include the section

### 4. UPDATING MAIN PAGE (src/app/page.tsx)

When adding a NEW SECTION to the homepage:
```typescript
// FILE: src/app/page.tsx
"use client";

import HeroSection from "@/components/hero-section/hero-section";
import FeaturesSection from "@/components/features-section/features-section";
import FAQSection from "@/components/faq-section/faq-section"; // NEW SECTION

export default function Home() {{
  return (
    <main className="min-h-screen">
      <HeroSection />
      <FeaturesSection />
      <FAQSection /> {{/* NEW SECTION ADDED */}}
    </main>
  );
}}
```

### 5. DATA FETCHING PATTERNS

**Client Component with Hooks:**
```typescript
"use client";

import {{ useProduct }} from "@/hooks/use-product";

export default function ProductList() {{
  const {{ data, isLoading, error }} = useProduct();
  
  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error loading products</div>;
  
  return <div>{{/* Render products */}}</div>;
}}
```

**Server Component (NO "use client"):**
```typescript
// NO "use client" directive - this is a server component
import {{ getProducts }} from "@/services/api/products";

export default async function ProductList() {{
  const products = await getProducts();
  
  return <div>{{/* Render products */}}</div>;
}}
```

### 6. TECHNICAL RULES (Prevent Build Errors)
1. **NO NEW DEPENDENCIES**: Only use existing libraries in package.json
2. **EXISTING HOOKS FIRST**: Always check `src/hooks/` before creating new data fetching logic
3. **EXISTING SERVICES**: Use `src/services/api/` for API calls, never raw fetch
4. **TYPE SAFETY**: Import types from `src/types/[type-name].ts`
5. **PATH ALIASES**: Use `@/` for all imports
6. **PROVIDER SAFETY**: Never remove QueryProvider or other context providers

### 7. DATA HANDLING & ERROR PREVENTION (CRITICAL)

#### A. API Response Structure for Lists
**ALL** list endpoints (products, orders, categories, etc.) return a **paginated object**, NOT an array.
**Response Shape**:
```typescript
{{
  results: ItemType[]; // The actual data array
  count: number;       // Total items
  pagination?: {{ ... }}; // Optional helper
}}
```

**CORRECT Usage (Hybrid Pattern)**:
```typescript
// ✅ ALWAYS use this safe pattern to handle both pagination and flat arrays
const items = data?.results || (Array.isArray(data) ? data : []);

{{items?.map((item) => (
  <Card key={{item.id}} />
))}}
```

#### B. DATA FETCHING STRICTNESS (NO DUMMY DATA)
1. **REAL DATA ONLY**: You must utilization existing hooks (e.g., `useProduct`, `useOrders`).
   - ❌ **FORBIDDEN**: `const dummyProducts = [...]`
   - ❌ **FORBIDDEN**: Commenting out `useProduct` to use static data.
   - ✅ **REQUIRED**: `const {{ data, isLoading }} = useProduct();`
2. **HOOKS PRIORITY**: Check `src/hooks/` folder. If a hook exists for the entity, you **MUST** use it.
3. **SERVER COMPONENTS**: When fetching data in server components (e.g. `page.tsx`), check `src/services/api/` for the correct function.
   - ❌ **FORBIDDEN**: Guessing functions like `getProductBySlug`, `getById`.
   - ✅ **REQUIRED**: Read the "API Services" section to find the EXACT export, e.g., `productApi.getProduct(slug)`.
4.  **HANDLING LOADING**: Always show a loading skeleton or spinner while fetching.

#### C. TYPE SAFETY & CASTING (PREVENT CRASHES)
1. **CHECK TYPES FIRST**: **EXTREMELY IMPORTANT**: Look at the "Project Types" section above. You MUST use the EXACT field names defined there.
   - ❌ **Wrong**: `image_url` (if not in type), `img`, `picture`
   - ✅ **Correct**: `thumbnail_image` (if in type), `slug`, `title`
2. **SAFE CASTING**: API data is often loose (strings instead of numbers).
   - **Prices**: `Number(product.price || 0).toFixed(2)` (Fixes "toFixed is not a function")
   - **Dates**: `new Date(order.created_at).toLocaleDateString()`
3. **OPTIONAL CHAINING**: usage `item?.property` is mandatory for nested objects.

### 8. AUTOMATIC DETAIL PAGE CREATION
When the user asks for a list page (e.g., "products", "services", "blogs"), YOU SHOULD ALSO:
1.  **Check for defined types**: Look at `src/types/` for the entity.
2.  **Create/Update the Detail Page**: If it's a list, ensure there is a corresponding dynamic route (e.g., `src/app/services/[slug]/page.tsx`).
3.  **Link them**: Ensure the list items link to the detail page.
4.  **Use Slug**: Always use `slug` for routing if available in the type definition.

## IMAGE HANDLING PROTOCOL

### Rule 1: STATIC IMAGES (Home, About Us, UI Decorators)
**Requirement**: Use `ImageWithFallback` + `images.json`.
-- **CONTEXT**: Only for static content that is hardcoded (Banner, Hero, promo sections).
-- **Implementation**:
```tsx
import ImageWithFallback from "@/components/common/ImageWithFallback";
import images from "@/../images.json";
// ...
<ImageWithFallback id="hero-main" src={{images.hero_main}} ... />
```

### Rule 2: DYNAMIC IMAGES (Products, Blogs, Listings)
**Requirement**: Use standard `next/image`.
-- **CONTEXT**: For ANY data coming from an API (Product lists, Blog posts, User avatars).
-- **RESTRICTION**: Do **NOT** use `ImageWithFallback` for dynamic data.
-- **PROPERTY**: Prioritize `thumbnail_image` (standard in this project).
-- **Implementation**:
```tsx
import Image from "next/image";
// ...
<div className="relative h-64 w-full">
  <Image
    src={{product.thumbnail_image || "/placeholder.png"}} // Prefer thumbnail_image
    alt={{product.name}}
    fill
    className="object-cover"
  />
</div>
```

## OUTPUT FORMAT SPECIFICATION

Output code in this exact format:

## FILE: src/app/about-us/page.tsx
```typescript
import AboutUs from "@/components/about-us/about-us";

export default function AboutUsPage() {{
  return <AboutUs />;
}}
```

## FILE: src/components/about-us/about-us.tsx
```typescript
"use client";

import {{ useCompany }} from "@/hooks/use-company";

export default function AboutUs() {{
  // Component code
}}
```

## FILE: src/app/page.tsx
```typescript
"use client";

import HeroSection from "@/components/hero-section/hero-section";
import AboutUsPreview from "@/components/about-us-preview/about-us-preview";

export default function Home() {{
  return (
    <main>
      <HeroSection />
      <AboutUsPreview />
    </main>
  );
}}
```

## DECISION FLOW FOR USER REQUESTS

**User says: "Create About Us page"**
→ Create `src/app/about-us/page.tsx` (Server Component)
→ Create `src/components/about-us/about-us.tsx` with "use client" if using hooks
→ Do NOT modify main page.tsx

**User says: "Add FAQ section to homepage"**
→ Create `src/components/faq-section/faq-section.tsx` with "use client"
→ Update `src/app/page.tsx` to import and include FAQSection

**User says: "Make product listing page"**
→ Create `src/app/products/page.tsx` (Server Component)
→ Create `src/components/product-list/product-list.tsx` with "use client"
→ Use `useProduct()` hook for data

**User says: "Create hero section"**
→ Create `src/components/hero-section/hero-section.tsx` with "use client" if interactive
→ Update `src/app/page.tsx` to include HeroSection

## IMPORTANT REMINDERS
- ✅ ALWAYS add "use client" when importing hooks
- ✅ ALWAYS add "use client" when using useState, useEffect, etc. (BUT prevent it on wrapper pages)
- ✅ ALWAYS create proper folder structure: app/[page]/page.tsx
- ✅ ALWAYS keep components in src/components/[name]/[name].tsx
- ✅ ALWAYS update main page.tsx when adding homepage sections
- ✅ NEVER remove existing providers or context wrappers
- ✅ NEVER create new dependencies without checking package.json
"""

        # 3. INITIALIZE AGENT
        try:
            agent = GeminiAgent(use_tools=False)
            print("✅ Agent initialized successfully.")
        except ValueError as e:
            os.chdir(original_cwd)
            return {
                "status": "error",
                "message": f"Failed to initialize agent: {str(e)}",
            }

        # 4. EXECUTE WORKFLOW
        print("\n" + "=" * 80)
        print("⚡ EXECUTING AI WORKFLOW")
        print("=" * 80)

        response = agent.send_message(system_prompt)

        conversation_log = []
        files_modified = []

        iteration = 0
        while iteration < max_iterations:
            iteration += 1
            print(f"\n🔄 Turn {iteration}")

            conversation_log.append({"iteration": iteration, "response": response})

            # PARSE RESPONSE FOR FILES
            if response["type"] == "final_answer":
                content = str(response["content"])
                print("🧠 AI Response received. Parsing files...")

                # Parse file markers
                if "## FILE:" in content:
                    segments = content.split("## FILE:")
                else:
                    segments = content.split("FILE:")

                found_files = False

                for i in range(1, len(segments)):
                    segment = segments[i]
                    lines = segment.strip().split("\n", 1)
                    if not lines:
                        continue

                    file_path = lines[0].strip()
                    if not file_path:
                        continue

                    print(f"🔍 Analyzing: {file_path}")

                    # Find code block
                    start_pattern = "```"
                    start_idx = segment.find(start_pattern)

                    if start_idx != -1:
                        newline_idx = segment.find("\n", start_idx)
                        if newline_idx != -1:
                            content_start = newline_idx + 1
                            end_idx = segment.find("```", content_start)

                            if end_idx != -1:
                                found_files = True
                                new_content = segment[content_start:end_idx]

                                # Validate "use client" directive for specific files
                                if _needs_use_client(file_path, new_content):
                                    if not new_content.strip().startswith(
                                        '"use client"'
                                    ):
                                        print(
                                            f"⚠️ Adding missing 'use client' to {file_path}"
                                        )
                                        new_content = '"use client";\n\n' + new_content

                                print(f"📦 Found file: {file_path}")

                                # Validate file path - PREVENT BACKEND FILE MODIFICATIONS
                                if _is_protected_file(file_path):
                                    print(
                                        f"🚫 BLOCKED: Cannot modify protected backend file: {file_path}"
                                    )
                                    print(
                                        "   Protected files: hooks/, services/, types/, schemas/, contexts/, lib/"
                                    )
                                    continue

                                # Handle deletion
                                if new_content.strip() == "<<DELETE>>":
                                    print(f"🗑️ Deleting: {file_path}")
                                    result = delete_file(file_path)
                                    if result["status"] == "success":
                                        files_modified.append(file_path + " (DELETED)")
                                        print(f"✅ Deleted: {file_path}")
                                else:
                                    # Write file
                                    result = write_file(file_path, new_content)
                                    if result["status"] == "success":
                                        files_modified.append(file_path)
                                        print(f"✅ Modified: {file_path}")
                                    else:
                                        print(f"❌ Failed: {result['message']}")

                if found_files:
                    print(
                        f"\n✅ Processing complete. Modified {len(files_modified)} files."
                    )

                    # Generate file tree
                    tree_data = None
                    try:
                        tree_data = generate_file_tree(
                            project_root, include_content=True
                        )
                    except Exception as tree_err:
                        print(f"⚠️ Failed to generate tree: {tree_err}")

                    # Send webhook
                    if webhook_url and tree_data:
                        try:
                            print(f"📣 Sending webhook to {webhook_url}...")
                            requests.post(webhook_url, json=tree_data, timeout=5)
                            print("✅ Webhook sent.")
                        except Exception as e:
                            print(f"⚠️ Webhook failed: {e}")

                    break
                else:
                    print("⚠️ No file blocks found.")

            elif response["type"] == "tool_calls":
                print("⚠️ Unexpected tool call in text-only mode.")
                tool_results = []
                for tool_call in response["tool_calls"]:
                    name = tool_call["name"]
                    args = tool_call["arguments"]
                    print(f"🛠️ Tool: {name}")
                    result = execute_tool(name, args)
                    tool_results.append({"name": name, "result": result})

                response = agent.send_tool_results(tool_results)
                continue

            elif response["type"] == "error":
                print(f"❌ Error: {response['content']}")
                break

            break

        os.chdir(original_cwd)

        print("\n" + "=" * 80)
        print(f"🎉 COMPLETE. Modified {len(files_modified)} files.")
        print("=" * 80 + "\n")

        return {
            "status": "success",
            "files_modified": list(set(files_modified)),
            "conversation_log": conversation_log,
            "iterations": iteration,
        }

    except Exception as e:
        os.chdir(original_cwd)
        import traceback

        traceback.print_exc()
        return {"status": "error", "message": str(e)}


def _needs_use_client(file_path: str, content: str) -> bool:
    """
    Determine if a file needs "use client" directive.
    """
    # Skip if already has "use client"
    if '"use client"' in content or "'use client'" in content:
        return False

    # Check for hooks imports
    hook_patterns = [
        "from 'react'",
        'from "react"',
        "useState",
        "useEffect",
        "useContext",
        "useReducer",
        "useCallback",
        "useMemo",
        "useRef",
        "from '@/hooks/",
        'from "@/hooks/',
    ]

    # Check for event handlers
    event_patterns = ["onClick", "onChange", "onSubmit", "onFocus", "onBlur"]

    # Check for browser APIs
    browser_patterns = ["window.", "document.", "localStorage", "sessionStorage"]

    all_patterns = hook_patterns + event_patterns + browser_patterns

    return any(pattern in content for pattern in all_patterns)


def _is_protected_file(file_path: str) -> bool:
    """
    Check if a file is in a protected directory that should never be modified.
    Protected directories: hooks/, services/, types/, schemas/, contexts/, lib/
    """
    protected_dirs = [
        "src/hooks/",
        "src/services/",
        "src/types/",
        "src/schemas/",
        "src/contexts/",
        "src/lib/",
        "src/components/common/ImageWithFallback.tsx",
        "src/components/providers/query-provider.tsx",
        # Also protect with different path separators
        "src\\hooks\\",
        "src\\services\\",
        "src\\types\\",
        "src\\schemas\\",
        "src\\contexts\\",
        "src\\lib\\",
    ]

    # Normalize path separators
    normalized_path = file_path.replace("\\", "/")

    # Check if file is in any protected directory
    return any(protected_dir in normalized_path for protected_dir in protected_dirs)


# Keep the function accessible at module level
def orchestrate_agent_wrapper(
    user_prompt: str,
    project_root: str,
    max_iterations: int = 5,
    webhook_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Wrapper function for backward compatibility."""
    return orchestrate_agent(user_prompt, project_root, max_iterations, webhook_url)
