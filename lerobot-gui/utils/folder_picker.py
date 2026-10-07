"""
Folder picker dialog for NiceGUI applications.
Adapted from NiceGUI local_file_picker example for folder selection.
"""

from pathlib import Path
from typing import Optional
from nicegui import ui, events


class local_folder_picker(ui.dialog):
    """
    Local folder picker dialog for selecting directories.

    Usage:
        result = await local_folder_picker('/path/to/start', upper_limit='/path/to/limit')
        if result:
            print(f"Selected: {result}")
    """

    def __init__(self, directory: str, *, upper_limit: Optional[str] = None) -> None:
        """
        Initialize folder picker.

        Args:
            directory: Starting directory path
            upper_limit: Optional upper directory limit (user cannot navigate above this)
        """
        super().__init__()

        self.path = Path(directory).expanduser()
        if not self.path.exists():
            self.path = Path.home()

        self.upper_limit = Path(upper_limit).expanduser() if upper_limit else None

        with self, ui.card().classes('w-[700px]'):
            ui.label('📁 Sélectionner un Dossier').classes('text-2xl font-bold mb-4')

            # Current path display
            self.path_label = ui.label(str(self.path)).classes(
                'text-sm text-gray-400 mb-2 font-mono break-all'
            )

            # Drive selector for Windows
            with ui.row().classes('w-full gap-2 mb-2'):
                self.drives_toggle = ui.toggle(
                    {d: d for d in self._get_drives()},
                    value=self._get_current_drive(),
                    on_change=self._handle_drive_change
                ).classes('w-full')

            # Folder grid
            self.grid = ui.aggrid({
                'columnDefs': [
                    {'field': 'name', 'headerName': 'Dossier', 'sortable': True}
                ],
                'rowSelection': {'mode': 'singleRow'},
            }, html_columns=[0]).classes('h-96 w-full').on(
                'cellDoubleClicked', self._handle_double_click
            )

            # Action buttons
            with ui.row().classes('w-full justify-end gap-2 mt-4'):
                ui.button('Annuler', on_click=self.close).props('outline')
                ui.button('Dossier Actuel', on_click=self._select_current).props('color=primary outline')
                ui.button('Sélectionner', on_click=self._handle_ok).props('color=primary')

        self.update_grid()

    def _get_drives(self) -> list[str]:
        """Get available drives (Windows) or root (Unix)."""
        try:
            # Windows: try to list drives
            import string
            from os import path
            drives = []
            for letter in string.ascii_uppercase:
                drive = f'{letter}:'
                if path.exists(drive):
                    drives.append(drive)
            return drives if drives else ['/']
        except:
            return ['/']

    def _get_current_drive(self) -> str:
        """Get current drive letter or root."""
        path_str = str(self.path)
        if len(path_str) >= 2 and path_str[1] == ':':
            return path_str[:2]
        return '/'

    def _handle_drive_change(self) -> None:
        """Handle drive selection change."""
        drive = self.drives_toggle.value
        if drive:
            self.path = Path(drive + '/')
            self.update_grid()

    def update_grid(self) -> None:
        """Update the folder grid with current directory contents."""
        self.path_label.text = str(self.path)

        # Update drive toggle
        current_drive = self._get_current_drive()
        if current_drive != self.drives_toggle.value:
            self.drives_toggle.value = current_drive

        # List only directories
        try:
            folders = [p for p in self.path.iterdir() if p.is_dir()]
            folders.sort(key=lambda p: p.name.lower())
        except PermissionError:
            folders = []
            ui.notify('⚠️ Accès refusé à ce dossier', type='warning')

        # Build row data
        row_data = []

        # Add ".." to go up if not at limit
        if self.upper_limit is None or self.path != self.upper_limit:
            if self.path.parent != self.path:  # Not at root
                row_data.append({
                    'name': '📁 <strong>..</strong>',
                    'path': str(self.path.parent),
                })

        # Add folders
        for folder in folders:
            row_data.append({
                'name': f'📁 <strong>{folder.name}</strong>',
                'path': str(folder),
            })

        self.grid.options['rowData'] = row_data
        self.grid.update()

    def _handle_double_click(self, e: events.GenericEventArguments) -> None:
        """Handle double-click on folder."""
        selected_path = Path(e.args['data']['path'])
        if selected_path.is_dir():
            self.path = selected_path
            self.update_grid()

    async def _handle_ok(self) -> None:
        """Handle OK button - select highlighted folder."""
        rows = await self.grid.get_selected_rows()
        if rows:
            self.submit(rows[0]['path'])
        else:
            self.submit(str(self.path))

    def _select_current(self) -> None:
        """Select current directory."""
        self.submit(str(self.path))
