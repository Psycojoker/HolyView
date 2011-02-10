#!/usr/bin/python
# -*- coding:Utf-8 -*-

#import couchdbkit

import cPickle
import urwid

from datetime import date

import louie

def D(text): open("DEBUG", "a").write("%s\n" % text)

commands = {}

def command(func, key, mode, doc):
    louie.connect(func, "%s_%s" % (key, mode))
    if doc:
        if commands.has_key(mode):
            commands[mode].append((key, doc))
        else:
            commands[mode] = [(key, doc)]

def get_documentations():
    for i in commands.keys():
        yield "%s" % i
        yield "=" * len(i)
        for a, b in commands[i]:
            yield "%s : %s" % (a, b)
        yield ""

def have_input(func):
    def _have_input(*args):
        # ugly, to get "self"
        if args[0].user_input.strip():
            func(*args)
    return _have_input

def update_main(func):
    def _update_main(*args):
        to_return = func(*args)
        louie.send("update_main")
        return to_return

    return _update_main

def follow_item(func):
    def _follow_item(*args):
        item = func(*args)
        self = args[0]

        a = 0
        for i in self.content:
            if i.original_widget.item == item:
                break
            a += 1
        self.position = a
        self.frame.get_body().set_focus(self.position)
        return item

    return _follow_item

def disconnect(func):
    def _disconnect(*args):
        map(lambda i: louie.disconnect(i(), "user_input_done"), louie.get_all_receivers(signal="user_input_done"))
        func(*args)
    return _disconnect

class State(object):
    def __init__(self, states_set, state):
        self.avalaible_states = states_set
        self.state = None
        self.set_state(state)
        louie.connect(self.set_state, "set state")
        louie.connect(self.get,       "get state")

    def set_state(self, state):
        if state not in self.avalaible_states:
            raise ValueError("Unknow state: %s, should be one of those %s" % (state, self.avalaible_states))
        self.state = state

    def get(self):
        return self.state

class Item():
    def __init__(self, name, finished=False, progress=None, urgence=0, importance=0, creation_date=date.today(), completion_date=None):
        self.name = name
        self.finished = finished
        self.progress = progress if progress else []
        self.urgence = urgence
        self.importance = importance
        self.creation_date = creation_date
        self.completion_date = completion_date

    def toggle(self):
        self.finished = not self.finished
        self.completion_date = date.today() if self.finished else None

    def remove_point(self):
        if self.progress:
            self.progress.pop()

    def add_point(self):
        D('"%s" got a new point' % self.name.encode("Utf-8"))
        self.progress.append(date.today())

    def more_urgence(self):
        self.urgence += 1

    def less_urgence(self):
        self.urgence -= 1
        if self.urgence < 0:
            self.urgence = 0

    def more_importance(self):
        self.importance += 1

    def less_importance(self):
        self.importance -= 1
        if self.importance < 0:
            self.importance = 0

class ItemList():
    def __init__(self):
        self.items = self._get_all()

    def __del__(self):
        "Always save on death to be sure not to lose datas"
        self.save()

    def get(self, full=False, urgence=False):
        if urgence:
            self.items = sorted(self.items, key=lambda x: -x.urgence)
        else:
            self.items = sorted(self.items, key=lambda x: -x.importance)
        if not full:
            return filter(lambda x: not x.finished, self.items)
        else:
            return self.items

    def _get_all(self):
        return cPickle.load(open("/home/psycojoker/.malistdb", "r"))

    def save(self):
        cPickle.dump(self.items, open("/home/psycojoker/.malistdb", "wb"))

    def add(self, *args):
        self.items.append(Item(*args))

    def remove(self, item):
        self.items.remove(item)

class ItemWidget(urwid.Text):
    def __init__(self, item):
        self.item = item
        super(ItemWidget, self).__init__(item.name)
        self.update()

    def update(self):
        text = []
        text.append('%i/%s ' % (self.item.importance, self.item.urgence))
        if not self.item.finished:
            text.append(self.item.name)
        else:
            text.append(('finished', self.item.name))

        text.append(" ")
        text.append(("old", "|"*len(self.item.progress)))
        self.set_text(text)

class HelpList(object):
    def __init__(self, frame, state):
        self.frame = frame
        self.state = state
        self.position = 0
        self.init_signals()

    def init_signals(self):
        command(self.exit,                  "q", "help", "return to main view")
        command(self.go_down,               "j" ,"help", "move the cursor down")
        command(self.go_up,                 "k", "help", "move the cursor up")
        command(self.go_down,               "down" ,"help", "move the cursor down")
        command(self.go_up,                 "up", "help", "move the cursor up")

    def exit(self):
        louie.send("update_main")

    def fill_list(self):
        self.content = [urwid.Text(i) for i in get_documentations()]
        self.content = urwid.SimpleListWalker([urwid.AttrMap(i, None, 'reveal focus') for i in self.content])
        self.frame.set_body(urwid.ListBox(self.content))
        self.state.set_state("help")

    def go_down(self):
        if self.position < (len(self.content) - 1):
            self.position += 1
            self.frame.get_body().set_focus(self.position)

    def go_up(self):
        if self.position > 0:
            self.position -= 1
            self.frame.get_body().set_focus(self.position)

class MainList(object):
    def __init__(self):
        self.item_list = ItemList()
        self.frame = None
        self.state = State(("main", "user_input_main", "help"), "main")
        self.content = [ItemWidget(i) for i in self.item_list.get()]
        self.content = urwid.SimpleListWalker([urwid.AttrMap(i, None, 'reveal focus') for i in self.content])
        self.frame = urwid.Frame(urwid.ListBox(self.content))
        self.footer = urwid.Edit("", "")
        self.frame.set_footer(self.footer)
        self.doc = HelpList(self.frame, self.state)
        self.init_signals()
        self.position = 0
        self.full_list = False
        self.urgence = False
        #self.fill_list()
        #self.show_key = urwid.Text("MaList 0.1", wrap='clip')
        #self.frame.set_header(urwid.AttrMap(self.show_key, 'header'))

    def get_state(self):
        return self.state.get()

    def run(self):
        palette = [('header', 'white', 'dark red'),
                   ('reveal focus', 'white', 'dark red', 'standout'),
                   ('realm', 'dark red', '', 'bold'),
                   ('quest', 'light green', '', 'bold'),
                   ('old', 'yellow', '', 'bold'),
                   ('date left', 'black', 'light cyan'),
                   ('date late', 'yellow', 'dark magenta'),
                   ('finished', 'dark cyan', ''),
                   ('mission', 'light gray', '')]

        urwid.MainLoop(self.frame, palette, input_filter=self.show_all_input, unhandled_input=self.manage_input).run()

    def fill_list(self):
        self.content = [ItemWidget(i) for i in self.item_list.get(self.full_list, self.urgence)]
        D(self.item_list.get())
        self.content = urwid.SimpleListWalker([urwid.AttrMap(i, None, 'reveal focus') for i in self.content])
        self.frame.set_body(urwid.ListBox(self.content))
        self.frame.get_body().set_focus(self.position)
        self.state.set_state("main")

    def init_signals(self):
        command(self.exit,                  "q", "main", "quit holyview")
        command(self.add_task,              "a", "main", "add a new item")
        command(self.go_down,               "j" ,"main", "move the cursor down")
        command(self.go_up,                 "k", "main", "move the cursor up")
        command(self.go_down,               "down" ,"main", "move the cursor down")
        command(self.go_up,                 "up", "main", "move the cursor up")
        command(self.remove_current_item,   "d", "main", "remove the current item")
        command(self.rename_current_item,   "r", "main", "rename the current item")
        command(self.toggle_current_item,   " ", "main", "toggle the current item (between finished and unfinished)")
        command(self.add_point,             "+", "main", "add a point the current item")
        command(self.remove_point,          "-", "main", "remove a point the current item")
        command(self.more_urgence,          "M", "main", "augment the urgence of the current item")
        command(self.less_urgence,          "L", "main", "lower the urgence of the current item")
        command(self.more_importance,       "m", "main", "augment the importance of the current item")
        command(self.less_importance,       "l", "main", "lower the importance of the current item")
        command(self.toggle_show_full_list, "h", "main", "toggle displaying the completed items")
        command(self.toggle_urgence_importance, "i", "main", "toggle displaying the completed items")
        command(self.doc.fill_list,         "?", "main", "display help")

        command(self.fill_list,             "update", "main", None)
        command(self.get_user_input_main,   "enter", "user_input_main", None)

    def show_all_input(self, input, raw):
        return input

    def manage_input(self, input):
        #if self.get_state() == "main":
            #self.main_view.position = self.frame.get_body().get_focus()[1]
        #D("%s_%s" % (input, self.get_state()))
        louie.send("%s_%s" % (input, self.get_state()))
        #if not louie.send("%s_%s" % (input, self.get_state())):
            # tuple == mouse input
            #self.show_key.set_text(input if not isinstance(input, tuple) else "%s, %s, %s, %s" % input)
        #if input == "q":
            #raise urwid.ExitMainLoop

    def go_down(self):
        if self.position < (len(self.content) - 1):
            self.position += 1
            self.frame.get_body().set_focus(self.position)

    def go_up(self):
        if self.position > 0:
            self.position -= 1
            self.frame.get_body().set_focus(self.position)

    @update_main
    def remove_current_item(self):
        self.item_list.remove(self._get_current_item())
        if self.position == len(self.content) - 1:
            self.position = len(self.content) - 2

    @follow_item
    @update_main
    def toggle_urgence_importance(self):
        self.urgence = not self.urgence
        return self._get_current_item()

    @update_main
    def toggle_show_full_list(self):
        self.full_list = not self.full_list

    def _get_current_widget(self):
        return self.frame.get_body().get_focus()[0].original_widget

    def _get_current_item(self):
        return self.frame.get_body().get_focus()[0].original_widget.item

    def exit(self):
        raise urwid.ExitMainLoop

    def rename_current_item(self):
        self._wait_for_input("New description: ", self.get_rename_current_item)

    @update_main
    def remove_point(self):
        self._get_current_item().remove_point()
        self._get_current_widget().update()

    @update_main
    def add_point(self):
        self._get_current_item().add_point()
        self._get_current_widget().update()

    @follow_item
    @update_main
    def more_urgence(self):
        self._get_current_item().more_urgence()
        self._get_current_widget().update()
        return self._get_current_item()

    @follow_item
    @update_main
    def less_urgence(self):
        self._get_current_item().less_urgence()
        self._get_current_widget().update()
        return self._get_current_item()

    @follow_item
    @update_main
    def more_importance(self):
        self._get_current_item().more_importance()
        self._get_current_widget().update()
        return self._get_current_item()

    @follow_item
    @update_main
    def less_importance(self):
        self._get_current_item().less_importance()
        self._get_current_widget().update()
        return self._get_current_item()

    @update_main
    def toggle_current_item(self):
        self._get_current_item().toggle()
        self._get_current_widget().update()

    @disconnect
    @have_input
    @update_main
    def get_rename_current_item(self):
        self._get_current_item().name = self.user_input
        self._get_current_widget().update()

    def add_task(self):
        self._wait_for_input("New item: ", self.get_add_task)

    @disconnect
    @have_input
    @update_main
    def get_add_task(self):
        self.item_list.add(self.user_input)

    def get_user_input_main(self):
        self.frame.set_focus('body')
        # debug
        #louie.send("show key", None, "Mission description: " + self.frame.footer.get_focus().edit_text)
        self.user_input = self.frame.footer.edit_text
        self.frame.footer.edit_text = ""
        self.frame.footer.set_caption("")
        louie.send("set state", None, "main")
        louie.send("user_input_done")

    def _wait_for_input(self, text, callback):
        self.frame.set_focus('footer')
        self.frame.get_footer().set_caption(text)
        louie.send("set state", None, "user_input_main")
        louie.connect(callback, "user_input_done")

if __name__ == "__main__":
    #cPickle.dump([Item("first item")], open("/home/psycojoker/.malistdb", "wb"))
    #ItemList().add("caca")
    #new_item("first item")
    #push_view()
    #a = ItemList()
    #for i in a.get():
        #i.progress = list()
    #a.save()
    MainList().run()

# vim:set shiftwidth=4 tabstop=4 expandtab:
