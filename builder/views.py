from django.shortcuts import render
from django.views.generic import TemplateView


class BuilderIDEView(TemplateView):
    template_name = "builder/ide.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if hasattr(self.request, "tenant"):
            context["workspace_id"] = self.request.tenant.schema_name
            context["repo_url"] = getattr(self.request.tenant, "repo_url", "")
        else:
            context["workspace_id"] = "public"
            context["repo_url"] = ""
        return context


# simple view function backup
def builder_ide(request):
    return render(request, "builder/ide.html")
