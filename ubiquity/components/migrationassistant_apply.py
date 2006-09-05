from ubiquity.filteredcommand import FilteredCommand

class MigrationAssistantApply(FilteredCommand):
    def prepare(self):
        return (['/usr/lib/ubiquity/migration-assistant/ma-apply',
		'/usr/lib/ubiquity/migration-assistant'], [])

    def error(self, priority, question):
        self.frontend.error_dialog(self.description(question))
        return super(MigrationAssistantApply, self).error(priority, question)
