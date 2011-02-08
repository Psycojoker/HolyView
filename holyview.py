#!/usr/bin/python
# -*- coding:Utf-8 -*-

#import couchdbkit

import cPickle
import urwid

from datetime import date

import louie

def D(text): open("DEBUG", "a").write("%s\n" % text)

def update_main(func):
    def _update_main(*args):
        func(*args)
        louie.send("update_main")

    return _update_main

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
    def __init__(self, name, finished=False, progress=0, difficulty=0, consequence=0, creation_date=date.today(), completion_date=None):
        self.name = name
        self.finished = finished
        self.progress = progress
        self.difficulty = difficulty
        self.consequence = consequence
        self.creation_date = creation_date
        self.completion_date = completion_date

class ItemList():
    def __init__(self):
        self.items = self._get_all()

    def __del__(self):
        "Always save on death to be sure not to lose datas"
        self.save()

    def get(self):
        return self.items

    def _get_all(self):
        return cPickle.load(open("/home/psycojoker/.malistdb", "r"))

    def save(self):
        cPickle.dump(self.items, open("/home/psycojoker/.malistdb", "wb"))

    def add(self, *args):
        self.items.append(Item(*args))

class ItemWidget(urwid.Text):
    def __init__(self, item):
        self.item = item
        super(ItemWidget, self).__init__(item.name)

    def update(self):
        self.set_text(self.item.name)

class MainList(object):
    def __init__(self):
        self.item_list = ItemList()
        self.init_signals()
        self.frame = None
        self.state = State(["main", "user_input_main"], "main")
        self.content = [ItemWidget(i) for i in self.item_list.get()]
        self.content = urwid.SimpleListWalker([urwid.AttrMap(i, None, 'reveal focus') for i in self.content])
        self.frame = urwid.Frame(urwid.ListBox(self.content))
        self.footer = urwid.Edit("", "")
        self.frame.set_footer(self.footer)
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
                   ('mission', 'light gray', '')]

        urwid.MainLoop(self.frame, palette, input_filter=self.show_all_input, unhandled_input=self.manage_input).run()

    def fill_list(self):
        self.content = [ItemWidget(i) for i in self.item_list.get()]
        D(self.item_list.get())
        self.content = urwid.SimpleListWalker([urwid.AttrMap(i, None, 'reveal focus') for i in self.content])
        self.frame.set_body(urwid.ListBox(self.content))
        self.frame.body.set_focus(0)
        self.state.set_state("main")

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

    def exit(self):
        raise urwid.ExitMainLoop

    def init_signals(self):
        louie.connect(self.exit,                           "q_main")
        louie.connect(self.add_task,                       "a_main")
        louie.connect(self.fill_list,                      "update_main")

        louie.connect(self.get_user_input_main,            "enter_user_input_main")

    def add_task(self):
        self._wait_for_input("New item: ", self.get_add_task)

    @disconnect
    #@have_input
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
    MainList().run()

# vim:set shiftwidth=4 tabstop=4 expandtab:
