import flet as ft


def tab(page):
    tabs = [
            ft.Tab(
                text="Contacts",
                content=ft.Container(
                    ft.Text("hello"),
                    ft.Text("im here"),
                )
            ),
        ]
    
    t = ft.Tabs(
        selected_index=1,
        animation_duration=300,
        tabs=tabs,
        expand=1,
    )

    main_container = ft.Row([

    
        ft.Container(
            t,
            expand=3,
            height=700,
            # bgcolor=ft.Colors.GREEN_ACCENT
        ),
        ft.Container(
            ft.Text("hello"),
            expand=1,
            height=700,
            bgcolor=ft.Colors.BLUE
        ),
        ft.Container(
            ft.Text("hello"),
            expand=2,
            height=700,
            bgcolor=ft.Colors.YELLOW
        ),
    ] 
    )
    return ft.View(
        route="/test",
        controls=[
            main_container
        ]
    
    )


