from selectolax.lexbor import LexborHTMLParser, create_tag

from .dev import dev_prefix
from webfluid.core.context import FluidContext
from webfluid.core.constants import DEBUG, PROCESSING, THEMES


async def manipulate_index(frontend_path, relative_path, framework, html_str):
    try: ctx = FluidContext.current()
    except RuntimeError: return html_str
    html = LexborHTMLParser(html_str)

    if DEBUG:
        for script in html.css("script"):
            src_old = script.attributes.get("src")
            if src_old is None: continue
            script.attrs["src"] = f"{dev_prefix}/{relative_path}{src_old}"

        for link in html.css("link"):
            href_old = link.attributes.get("href")
            if href_old is None: continue
            href_old = href_old.lstrip("/")
            if (frontend_path / "public" / href_old).exists():
                link.attrs["href"] = f"{dev_prefix}/{relative_path}/public/{href_old}"
            else:
                link.attrs["href"] = f"{dev_prefix}/{relative_path}/{href_old}"

        client = create_tag("script")
        client.attrs["type"] = "module"
        client.attrs["src"] = f"{dev_prefix}/@vite/client"
        html.head.insert_child(client)

        if framework == "react":
            refresh = create_tag("script")
            refresh.attrs["type"] = "module"
            refresh.insert_child(f"""
                    import RefreshRuntime from "{dev_prefix}/@react-refresh";
                    RefreshRuntime.injectIntoGlobalHook(window);
                    window.$RefreshReg$ = () => {{}};
                    window.$RefreshSig$ = () => (type) => type;
                    window.__vite_plugin_react_preamble_installed__ = true;
                """)
            html.head.insert_child(refresh)

    theme = ctx.fluid.get_theme() if THEMES else ""
    if PROCESSING:
        src = await ctx.fluid.render(
            f"{theme}" + "{{ src() }}",
            is_string=True
        )

    else: src = "\n\t".join([theme, *ctx.fluid.sources])

    node = LexborHTMLParser(src).head
    if node: html.head.insert_child(node)

    return html.html
