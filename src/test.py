import flet as ft

import random

colors = {
    "red" : ft.Colors.RED,
    "blue" : ft.Colors.BLUE,
    "white" : ft.Colors.WHITE,
    "black" : ft.Colors.BLACK,
    "grey" : ft.Colors.GREY,
    "green" : ft.Colors.GREEN
}

print(random.choice(list(colors.items())))
# print(colors.blue)