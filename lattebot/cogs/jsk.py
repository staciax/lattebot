# https://github.com/Gorialis/jishaku

from __future__ import annotations

import contextlib
import inspect
import io
import logging
import os
import pathlib
from typing import TYPE_CHECKING, Any, Callable  # noqa: UP035

import discord
from discord import app_commands
from discord.app_commands import AppCommandError, locale_str as _
from discord.app_commands.checks import bot_has_permissions
from discord.ext import commands
from discord.ext.commands import Context
from discord.ext.commands.view import StringView
from jishaku.codeblocks import Codeblock, codeblock_converter
from jishaku.cog import STANDARD_FEATURES
from jishaku.exception_handling import ReplResponseReactor
from jishaku.features.baseclass import Feature
from jishaku.functools import AsyncSender
from jishaku.paginators import PaginatorInterface, WrappedPaginator, use_file_check
from jishaku.repl import AsyncCodeExecutor, get_var_dict_from_ctx  # type: ignore[attr-defined]

if TYPE_CHECKING:
    from lattebot.core.bot import LatteBot

log = logging.getLogger('latte.cogs.jsk')

os.environ['JISHAKU_NO_UNDERSCORE'] = 'True'
os.environ['JISHAKU_HIDE'] = 'True'


def owner_only[T]() -> Callable[[T], T]:
    async def actual_check(interaction: discord.Interaction[LatteBot]) -> bool:
        return await interaction.client.is_owner(interaction.user)

    return app_commands.check(actual_check)


class Jishaku(*STANDARD_FEATURES, name='jishaku'):  # type: ignore[misc]
    bot: LatteBot

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.ctx_message_jsk_py = app_commands.ContextMenu(
            name=_('Python'),
            callback=self.ctx_message_jishaku_python,
            guild_ids=[self.bot.support_guild_id],
        )
        self.ctx_message_jsk_py.error(self.cog_app_command_error)
        setattr(self.ctx_message_jsk_py, '__binding__', self)  # noqa: B010

    async def cog_load(self) -> None:
        self.bot.tree.add_command(self.ctx_message_jsk_py)
        await super().cog_load()

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.ctx_message_jsk_py.name, type=self.ctx_message_jsk_py.type)
        await super().cog_unload()

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction[LatteBot],
        error: app_commands.AppCommandError,
    ) -> None:
        interaction.client.dispatch('app_command_error', interaction, error)

    async def cog_check(self, ctx: commands.Context[LatteBot]) -> bool:
        if not await ctx.bot.is_owner(ctx.author):
            raise commands.NotOwner('You must own this bot to use Jishaku.')
        return True

    async def interaction_check(self, interaction: discord.Interaction[LatteBot]) -> bool:
        if not await interaction.client.is_owner(interaction.user):
            raise AppCommandError('You must own this bot to use Jishaku.')
        return super().interaction_check(interaction)  # type: ignore[no-any-return]

    @Feature.Command(name='jishaku', aliases=['jsk'], invoke_without_command=True, ignore_extra=False)  # type: ignore[arg-type]
    async def jsk(self, ctx: commands.Context[LatteBot]) -> None:
        """Display the Jishaku debug and diagnostic commands.

        This command on its own gives a status brief.
        All other functionality is within its subcommands.
        """
        embed = discord.Embed(
            title='Jishaku',
            description=f'Jishaku is a debug and diagnostic cog for **{self.bot.user}**.',
            color=discord.Color.blurple(),
        )
        await ctx.send(embed=embed, silent=True)

    @Feature.Command(parent='jsk', name='source', aliases=['src'])  # type: ignore[arg-type, call-arg]
    async def jsk_source(self, ctx: commands.Context[LatteBot], *, command_name: str) -> None:
        """Display the source code for an app command."""
        # NOTE: custom for support app command

        command = self.bot.get_command(command_name) or self.bot.tree.get_command(command_name)
        if not command:
            await ctx.send(f"Couldn't find command `{command_name}`.")
            return

        try:
            source_lines, _ = inspect.getsourcelines(command.callback)  # type: ignore[union-attr]
        except (TypeError, OSError):
            await ctx.send(f'Was unable to retrieve the source for `{command}` for some reason.')
            return

        filename = 'source.py'

        with contextlib.suppress(TypeError, OSError):
            filename = pathlib.Path(inspect.getfile(command.callback)).name  # type: ignore[union-attr]

        # getsourcelines for some reason returns WITH line endings
        source_text = ''.join(source_lines)

        if use_file_check(ctx, len(source_text)):  # File "full content" preview limit
            await ctx.send(
                file=discord.File(
                    filename=filename,
                    fp=io.BytesIO(source_text.encode('utf-8')),
                ),
                # ephemeral=True,
                # ephemeral=ctx.author != self.bot.owner,
            )
        else:
            paginator = WrappedPaginator(prefix='```py', suffix='```', max_size=1900)

            paginator.add_line(source_text.replace('```', '``\N{ZERO WIDTH SPACE}`'))

            interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
            # TODO: ephemeral message
            await interface.send_to(ctx)

    @Feature.Command(parent='jsk', name='py', aliases=['python'])  # type: ignore[arg-type]
    async def jsk_python(
        self,
        ctx: commands.Context[LatteBot],
        *,
        argument: codeblock_converter,  # type: ignore[valid-type]
    ) -> None:
        """Direct evaluation of Python code."""
        if TYPE_CHECKING:
            argument: Codeblock = argument  # type: ignore[no-redef]  # noqa: PLW0127

        arg_dict = get_var_dict_from_ctx(ctx, '')
        arg_dict.update(get_var_dict_from_ctx(ctx, '_'))
        arg_dict['_'] = self.last_result  # type: ignore[has-type]

        scope = self.scope

        try:
            async with ReplResponseReactor(ctx.message):
                with self.submit(ctx):
                    executor = AsyncCodeExecutor(argument.content, scope, arg_dict=arg_dict)  # type: ignore[attr-defined]
                    async for send, result in AsyncSender(executor):  # type: ignore[arg-type, var-annotated]
                        send: Callable[..., None]  # type: ignore[no-redef]
                        result: Any  # type: ignore[no-redef]

                        if result is None:
                            continue

                        self.last_result = result

                        send(await self.jsk_python_result_handling(ctx, result))

        finally:
            scope.clear_intersection(arg_dict)

    @app_commands.command(name=_('jsk'))
    @app_commands.describe(sub=_('Sub command of jsk'), args=_('Arguments of jsk'))
    @app_commands.rename(sub=_('sub'), args=_('args'))
    @app_commands.default_permissions(administrator=True)
    @bot_has_permissions(send_messages=True, embed_links=True, add_reactions=True)
    @owner_only()
    async def jishaku_app(
        self,
        interaction: discord.Interaction[LatteBot],
        sub: app_commands.Range[str, 1, 20] | None = None,
        args: str | None = None,
    ) -> None:
        """Jishaku.

        Attributes
        ----------
            sub (str): The subcommand to use.
            args (str): The arguments to pass to the subcommand.
        """
        await interaction.response.defer(ephemeral=True)

        command = self.bot.get_command(f'jishaku {sub}' if sub else 'jishaku')

        if not command:
            raise AppCommandError(f"Couldn't find command `jishaku {sub}`.")

        ctx = await self.bot.get_context(interaction)
        ctx.invoked_with = command.qualified_name
        ctx.command = command
        if args:
            ctx.view = StringView(args)
        await self.bot.invoke(ctx)

    @jishaku_app.autocomplete('sub')
    async def jishaku_app_autocomplete(
        self,
        _interaction: discord.Interaction[LatteBot],
        current: str,
    ) -> list[app_commands.Choice[str]]:
        sub_commands: list[str] = []

        for command in self.walk_commands():
            if command is self.jsk:
                continue

            sub_commands.append(command.qualified_name)
            sub_commands.extend(command.aliases)

        # remove jishaku prefix, sort
        sub_commands = [sub.removeprefix('jishaku ') for sub in sub_commands]
        sub_commands = sorted(sub_commands)

        if not current:
            return [app_commands.Choice(name=sub, value=sub) for sub in sub_commands][:25]

        return [app_commands.Choice(name=sub, value=sub) for sub in sub_commands if current.lower() in sub][:25]

    @app_commands.default_permissions(administrator=True)
    @bot_has_permissions(send_messages=True, embed_links=True, add_reactions=True)
    @owner_only()
    async def ctx_message_jishaku_python(
        self,
        interaction: discord.Interaction[LatteBot],
        message: discord.Message,
    ) -> None:
        content = message.clean_content.strip()

        if not content:
            raise AppCommandError('No code provided.')

        await interaction.response.defer(ephemeral=content.startswith('_'))

        content = content.removeprefix('_')

        # jsk_py = self.bot.get_command('jishaku py')
        ctx = await Context.from_interaction(interaction)  # await self.bot.get_context(interaction)
        codeblock = codeblock_converter(content)

        try:
            await self.jsk_python(ctx, argument=codeblock)
        except Exception as e:
            log.exception('Jishaku Python command failed.', exc_info=e)
            raise AppCommandError('Invalid Python code.') from e


async def setup(bot: LatteBot) -> None:
    await bot.add_cog(Jishaku(bot=bot), guilds=[discord.Object(id=bot.support_guild_id)])
