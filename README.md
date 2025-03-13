# Firecrawl - Open-WebUI-Pipelines

**Firecrawl - Open-WebUI-Pipelines** is a collection of Python-based functions designed to extend the capabilities of [Open WebUI](https://github.com/open-webui) with additional **pipelines**. These pipelines allow users to interact with Firecrawl API, and customize the Open WebUI experience.

---

## Features

- **Firecrawl Integration**: Web crawling, Scraping, and URL mapping capabilities through [Firecrawl](https://www.firecrawl.dev/) API.
- **Flexible Configuration**: Use environment variables to adjust pipeline settings dynamically.

---

## Prerequisites

To use these pipelines, ensure the following:

1. **An Active Open WebUI Instance**: You must have [Open WebUI](https://github.com/open-webui/open-webui) installed and running.
2. **Firecrawl API Access**: You'll need to create an account and obtain an API key from [Firecrawl](https://www.firecrawl.dev/).
3. **Admin Access**: To install pipelines in Open WebUI, you must have administrator privileges.

---

## Installation

To install and configure pipelines in Open WebUI, follow these steps:

1. **Ensure Admin Access**:
   - You must be an admin in Open WebUI to install pipelines.

2. **Access Admin Settings**:
   - Navigate to the **Admin Settings** section in Open WebUI.

3. **Go to the Function Tab**:
   - Open the **Functions** tab in the admin panel.

4. **Create a New Function**:
   - Click **Add New Function**.
   - Copy the pipeline code from this repository and paste it into the function editor.

5. **Set Environment Variables (if required)**:
   - The Firecrawl pipelines require an API key via environment variables.
   - Set [WEBUI_SECRET_KEY](https://docs.openwebui.com/getting-started/env-configuration/#webui_secret_key) for secure encryption of sensitive API keys.

6. **Save and Activate**:
   - Save the function, and it will be available for use within Open WebUI.

---

## Pipelines

### **Firecrawl Pipelines**

Firecrawl is a powerful API service that takes a URL, crawls it, and converts it into clean markdown. We crawl all accessible subpages and give you clean LLM-ready data.

The following pipelines integrate Firecrawl with Open WebUI:

#### **[Firecrawl Web Crawling](./pipelines/firecrawl_crawl.py)**
- Crawls websites to extract content from multiple pages
- Configurable crawl depth and URL limits
- Support for path inclusion/exclusion patterns
- Sitemap integration for efficient crawling
- Handles both internal and external links

#### **[Firecrawl Web Scraping](./pipelines/firecrawl_scrape.py)**
- Extracts content from specific URLs
- Multiple output formats (markdown, HTML, text)
- Main content extraction to filter out navigation, ads, etc.
- Custom tag inclusion/exclusion
- Mobile device emulation
- Ad blocking capabilities

#### **[Firecrawl URL Mapping](./pipelines/firecrawl_map.py)**
- Discovers all URLs on a website
- Search functionality to find specific URLs
- Sitemap integration
- Subdomain discovery
- URL pattern matching

#### **[Firecrawl Data Extraction](./pipelines/firecrawl_extract.py)**
- Structured data extraction from websites using a specified prompt and schema
- Supports multiple URLs
- Options to enable web search, ignore sitemaps, include subdomains, and show sources
- Customizable scrape options

To use the Firecrawl pipelines, you need to:
1. Create a Firecrawl account at [https://www.firecrawl.dev/app/api-keys](https://www.firecrawl.dev/app/api-keys)
2. Generate an API key from the dashboard
3. Configure the pipeline with your API key

For detailed documentation on the Firecrawl API, visit [https://docs.firecrawl.dev/api-reference/introduction](https://docs.firecrawl.dev/api-reference/introduction)

For support with Firecrawl, contact [help@firecrawl.com](mailto:help@firecrawl.com)

🔗 [Firecrawl GitHub Repository](https://github.com/mendableai/firecrawl) - Give it a star ⭐️ to support the project!

---

## Contribute

Contributions are welcome! We appreciate your interest in improving these pipelines. You can contribute in several ways:

- **Open an Issue**: Have suggestions, found a bug, or want to request a feature? Create an issue to let us know.
- **Submit a Pull Request**: Have improvements or fixes ready? Submit a PR with your changes.
- **Share Feedback**: Your insights on how to make these pipelines better are valuable to us.

We review all contributions and will work with you to get them integrated. Thank you for helping make this project better!

## License 📜

This project is licensed under the [MIT License](LICENSE) - see the [LICENSE](LICENSE) file for details. 📄

## Support 💬

If you have any questions, suggestions, or need assistance, please open an issue or join our [Discord community](https://discord.com/invite/gSmWdAkdwd) to connect with us! 🤝

For Firecrawl-specific support, contact [help@firecrawl.com](mailto:help@firecrawl.com).

## Connect with Firecrawl

Follow us on social media to stay updated with the latest news and features:

- 𝕏: [@firecrawl_dev](https://x.com/firecrawl_dev)
- LinkedIn: [Firecrawl](https://www.linkedin.com/company/firecrawl/posts/?feedView=all)