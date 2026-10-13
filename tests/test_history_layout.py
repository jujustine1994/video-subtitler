from tkinter import font


def test_history_has_readable_rows_and_expands_with_window(app_factory):
    app, win, _ = app_factory('zh_tw')
    win.update_idletasks()
    from tkinter import ttk
    style = ttk.Style(win)
    rowheight = int(style.lookup(app.pending_tree.cget('style') or 'Treeview', 'rowheight') or 0)
    assert rowheight >= font.nametofont('TkDefaultFont').metrics('linespace') + 8
    assert int(app.pending_tree.cget('height')) >= 6
    assert int(win.grid_rowconfigure(5)['weight']) > 0
    assert app.pending_tree.grid_info()['sticky'] == 'nesw'
    assert int(app.pending_tree.column('file')['minwidth']) >= 350
    assert int(app.pending_tree.column('service')['minwidth']) >= 220
