from webfluid.exceptions import FrameworkException


async def _load_translations(babel, domains):
    from webfluid.extensions.babel.translations import TransactionService

    _domains = [domains.default_domain.domain]
    for domain in domains.store.values():
        _domains.append(domain.domain)

    tasks = []
    for domain in _domains:
        for locale in babel.supported_locales:
            tasks.append(
                TransactionService.load(locale, domain)
            )

    for task in tasks: await task


class Translations:
    def __init__(self, update_disabled):
        self._update_tasks = []
        self._update_blocked = False
        self._update_disabled = update_disabled

    async def startup_hook(self, babel, domains):
        if not self._update_disabled: await self._update_translations()
        await _load_translations(babel, domains)

    def update_translations(self, domain, translations):
        if self._update_disabled: return

        if self._update_blocked:
            raise FrameworkException("Translation updates are not allowed after startup.")

        from webfluid.extensions.babel.translations import TransactionService
        self._update_tasks.append(
            TransactionService.update(domain, translations)
        )

    async def _update_translations(self):
        self._update_blocked = True
        if not self._update_tasks: return
        for task in self._update_tasks: await task
        self._update_tasks = []
