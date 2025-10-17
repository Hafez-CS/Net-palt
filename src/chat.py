import flet as ft
import models

def get_all_users():
    models.init_db()
    users = models.get_all_users_db()
    return users


    
class contact:
    def __init__(self, name, image_path):
        self.name = name
        self.image_path = image_path
        
        self.container = ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        ft.CircleAvatar(
                        content=ft.Image(src=self.image_path),
                        radius=20,
                       ),
                       border_radius=30,
                    )
                    ,
                    ft.Text(self.name, size=16)
                ],
                alignment=ft.MainAxisAlignment.START,
                spacing=10,
            ),
            padding=ft.padding.all(10),
            width=280,
            height=65,
            border_radius=10,
            alignment=ft.alignment.center_left,
            ink=True,
            on_click=self.on_click
        )

    def on_click(self, e):
        print(f"Contact {self.name} clicked!")


def user_chat(page):

    username = page.session.get("current_username")
    def show_messege(e):
        msg = text_input.value
        if msg:
            username_span = f"- {username}: "
            
            chat_list_view.controls.append(
                ft.Text(
                    spans=[
                        ft.TextSpan(username_span, style= ft.TextStyle(size=16, color="#787878", italic=True)),
                        ft.TextSpan(msg)
                        ],
                        size=18
                        )
                    )
            text_input.value = ""
            page.update()


    main_container = ft.Container(
        content= ft.ListView(
            width=450,
            height=600,
            expand=True,
        ),
        border_radius=10,
        width=450,
        bgcolor="#002A46",
    )

    #it contains the messages
    chat_list_view =  ft.ListView(
                    controls=[ft.Text("Chat with Alice", size=20, weight=ft.FontWeight.BOLD),],
                    expand=True,
                )
    #these are buttons and the text input
    select_file_button = ft.IconButton(ft.Icons.FILE_OPEN,
                                        on_click=lambda e: print("file open clicked")
                                        )
    text_input = ft.TextField(
        label="Type a message",
        expand=True,
        border_radius=10,
        bgcolor="#004466",
        color=ft.Colors.WHITE,
        focused_border_color=ft.Colors.BLUE_200,
        height=50,
        on_submit= show_messege
    )

    send_button = ft.IconButton(ft.Icons.SEND,
                                 on_click=show_messege
                                 )
    
    #containing all the controls that handels the messages
    chat_container = ft.Container(
        ft.Column([

            ft.Container(
                chat_list_view,
                expand=True,
                border_radius=10,
                bgcolor="#001F2E",
                padding=ft.padding.all(10)

            ),

            ft.Row(
                [
                    select_file_button,
                    text_input,
                    send_button,
                ],
                alignment=ft.MainAxisAlignment.END,
            ),
            

        ],
        alignment=ft.MainAxisAlignment.END,
        ),
        bgcolor="#002D44",
        border_radius=10,
        expand=True,
        height=600,
        alignment=ft.alignment.bottom_center,
        padding=ft.padding.all(30)

    )

    users = get_all_users()

    for user in users:
        contact_container = contact(user, "assets/profile.png").container
        main_container.content.controls.append(contact_container)

        
    return ft.View(
        "/main",
        [
            ft.Row(controls=[
                main_container,
                chat_container]

            )
        ],
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.START,
        auto_scroll=True,
        appbar= ft.AppBar(
            title=ft.Text(f"Chat as {username} 💬"),
            center_title=True,
            bgcolor="#001F2E",
            actions=[
                ft.IconButton(ft.Icons.SEARCH, on_click=lambda e: print("Search clicked")),
                ft.IconButton(ft.Icons.MORE_VERT, on_click=lambda e: print("More clicked")),
            ],
        )

    )

if __name__ == "__main__":
    ft.app(target=user_chat)