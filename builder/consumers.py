import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .file_service import FileService


class LiveEditConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.workspace_id = self.scope["url_route"]["kwargs"]["workspace_id"]
        self.room_group_name = f"workspace_{self.workspace_id}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

        self.file_service = await sync_to_async(FileService)(self.workspace_id)

        # Automatic Repo Fetch
        try:

            def get_repo_info_sync(workspace_id):
                from tenants.models import Client

                tenant = Client.objects.filter(schema_name=workspace_id).first()
                if tenant:
                    return tenant.repo_url
                return None

            repo_url = await sync_to_async(get_repo_info_sync)(self.workspace_id)

            if repo_url:
                # Check if workspace needs initialization
                path_exists = await sync_to_async(self.file_service.base_path.exists)()

                if not path_exists:
                    import os

                    token = os.getenv("GITHUB_TOKEN")
                    await sync_to_async(self.file_service.clone_repo)(repo_url, token)
        except Exception as e:
            print(f"Error fetching repo on connect: {e}")

        tree = await sync_to_async(self.file_service.generate_tree)()
        await self.send(text_data=json.dumps(tree))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            action = data.get("action")
            print(f"[{self.room_group_name}] Received action: {action}")

            if action == "open_file":
                path = data.get("path")
                print(f"Opening file: {path}")
                content = await sync_to_async(self.file_service.read_file)(path)
                await self.send(
                    text_data=json.dumps(
                        {"action": "file_content", "path": path, "content": content}
                    )
                )

            elif action == "update_file":
                path = data.get("path")
                print(f"Updating file: {path}")
                content = data.get("content")
                await sync_to_async(self.file_service.write_file)(path, content)

                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "file_updated_event",
                        "path": path,
                        "sender_channel_name": self.channel_name,
                    },
                )

                await self.send(
                    text_data=json.dumps({"action": "file_updated", "path": path})
                )

            elif action == "delete_file":
                path = data.get("path")
                print(f"Deleting file: {path}")
                await sync_to_async(self.file_service.delete_file)(path)

                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "file_deleted_event",
                        "path": path,
                        "sender_channel_name": self.channel_name,
                    },
                )

                await self.send(
                    text_data=json.dumps({"action": "file_deleted", "path": path})
                )

            elif action == "rename_file":
                old_path = data.get("old_path")
                new_path = data.get("new_path")
                print(f"Renaming file from {old_path} to {new_path}")
                await sync_to_async(self.file_service.rename_file)(old_path, new_path)

                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "file_renamed_event",
                        "old_path": old_path,
                        "new_path": new_path,
                        "sender_channel_name": self.channel_name,
                    },
                )

                await self.send(
                    text_data=json.dumps(
                        {
                            "action": "file_renamed",
                            "old_path": old_path,
                            "new_path": new_path,
                        }
                    )
                )

            elif action == "create_file":
                path = data.get("path")
                content = data.get("content", "")
                print(f"Creating file: {path}")
                await sync_to_async(self.file_service.write_file)(path, content)

                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "file_created_event",
                        "path": path,
                        "sender_channel_name": self.channel_name,
                    },
                )

                await self.send(
                    text_data=json.dumps({"action": "file_created", "path": path})
                )

            elif action == "create_folder":
                path = data.get("path")
                print(f"Creating folder: {path}")
                await sync_to_async(self.file_service.create_directory)(path)

                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "folder_created_event",
                        "path": path,
                        "sender_channel_name": self.channel_name,
                    },
                )

                await self.send(
                    text_data=json.dumps({"action": "folder_created", "path": path})
                )

            elif action == "get_tree":
                print("Generating tree...")
                tree = await sync_to_async(self.file_service.generate_tree)()
                await self.send(text_data=json.dumps(tree))

            elif action == "github_clone":
                repo_url = data.get("repo_url")
                token = data.get("token")
                print(f"Cloning repo: {repo_url}")
                await sync_to_async(self.file_service.clone_repo)(repo_url, token)

                tree = await sync_to_async(self.file_service.generate_tree)()
                await self.send(text_data=json.dumps(tree))

            elif action == "github_push":
                message = data.get("message")
                token = data.get("token")
                print("Pushing changes to GitHub...")
                await sync_to_async(self.file_service.push_changes)(message, token)
                print("Push successful. Workspace deleted.")

                await self.channel_layer.group_send(
                    self.room_group_name, {"type": "workspace_deleted_event"}
                )

                await self.send(text_data=json.dumps({"action": "workspace_deleted"}))
            elif action == "reclone_project":
                print("Re-cloning project...")
                try:
                    # 1. Fetch Repo URL
                    def get_repo_info_sync(workspace_id):
                        from tenants.models import Client

                        tenant = Client.objects.filter(schema_name=workspace_id).first()
                        if tenant:
                            return tenant.repo_url
                        return None

                    repo_url = await sync_to_async(get_repo_info_sync)(
                        self.workspace_id
                    )

                    if repo_url:
                        # 2. Get Token
                        import os

                        token = os.getenv("GITHUB_TOKEN")

                        # 3. Clone (FileService.clone_repo handles cleanup)
                        await sync_to_async(self.file_service.clone_repo)(
                            repo_url, token
                        )

                        # 4. Send new tree
                        tree = await sync_to_async(self.file_service.generate_tree)()
                        await self.send(text_data=json.dumps(tree))

                        await self.send(
                            text_data=json.dumps(
                                {
                                    "action": "notification",
                                    "message": "Project re-cloned successfully",
                                }
                            )
                        )
                    else:
                        await self.send(
                            text_data=json.dumps(
                                {
                                    "action": "error",
                                    "message": "Repository URL not found for this workspace",
                                }
                            )
                        )
                except Exception as e:
                    print(f"Error re-cloning project: {e}")
                    await self.send(
                        text_data=json.dumps(
                            {
                                "action": "error",
                                "message": f"Failed to re-clone: {str(e)}",
                            }
                        )
                    )

            elif action == "install_project":
                print("Installing dependencies...")
                try:
                    from project_runner.services import RunnerService

                    await self.send(
                        text_data=json.dumps(
                            {
                                "action": "notification",
                                "message": "Installing dependencies...",
                            }
                        )
                    )

                    runner = await sync_to_async(RunnerService)(self.workspace_id)
                    success, message = await sync_to_async(
                        runner.install_dependencies
                    )()

                    if success:
                        await self.send(
                            text_data=json.dumps(
                                {
                                    "action": "notification",
                                    "message": "Dependencies installed successfully",
                                }
                            )
                        )
                    else:
                        await self.send(
                            text_data=json.dumps(
                                {
                                    "action": "error",
                                    "message": f"Installation failed: {message}",
                                }
                            )
                        )

                except Exception as e:
                    print(f"Error installing dependencies: {e}")
                    await self.send(
                        text_data=json.dumps({"action": "error", "message": str(e)})
                    )

            elif action == "run_project":
                print("Running project...")

                from project_runner.services import RunnerService

                try:
                    runner = await sync_to_async(RunnerService)(self.workspace_id)
                    result = await sync_to_async(runner.run_project)()

                    await self.send(
                        text_data=json.dumps(
                            {
                                "action": "nextjs_port",
                                "port": result["port"],
                                "url": result["url"],
                                "pid": result["pid"],
                            }
                        )
                    )

                except Exception as e:
                    print("Error running project:", e)
                    await self.send(
                        text_data=json.dumps({"action": "error", "message": str(e)})
                    )

        except Exception as e:
            print(f"Error in consumer: {e}")
            await self.send(text_data=json.dumps({"error": str(e)}))

    async def file_updated_event(self, event):
        if self.channel_name != event.get("sender_channel_name"):
            await self.send(
                text_data=json.dumps({"action": "file_updated", "path": event["path"]})
            )

    async def workspace_deleted_event(self, event):
        await self.send(text_data=json.dumps({"action": "workspace_deleted"}))

    async def file_deleted_event(self, event):
        if self.channel_name != event.get("sender_channel_name"):
            await self.send(
                text_data=json.dumps({"action": "file_deleted", "path": event["path"]})
            )

    async def file_renamed_event(self, event):
        if self.channel_name != event.get("sender_channel_name"):
            await self.send(
                text_data=json.dumps(
                    {
                        "action": "file_renamed",
                        "old_path": event["old_path"],
                        "new_path": event["new_path"],
                    }
                )
            )

    async def file_created_event(self, event):
        if self.channel_name != event.get("sender_channel_name"):
            await self.send(
                text_data=json.dumps({"action": "file_created", "path": event["path"]})
            )

    async def folder_created_event(self, event):
        if self.channel_name != event.get("sender_channel_name"):
            await self.send(
                text_data=json.dumps(
                    {"action": "folder_created", "path": event["path"]}
                )
            )
