        """Generate detailed schema context for LLM"""
        context = "# SCHEMA CONTEXT\n\n"
        
        for name, table in self.tables.items():
            context += f"## Table: {table.name}\n"
            context += f"**Purpose:** {table.purpose}\n\n"
            context += "**Columns:**\n"
            
            for col in table.columns:
                flags = []
                if col.is_primary_key:
                    flags.append("PRIMARY KEY")
                if col.foreign_key:
                    flags.append(f"FOREIGN KEY → {col.foreign_key}")
                if not col.is_nullable:
                    flags.append("NOT NULL")
                
                flag_str = f" [{', '.join(flags)}]" if flags else ""
                context += f'- "{col.name}" ({col.data_type}){flag_str}\n'
                context += f"  Purpose: {col.purpose}\n"
            
            if table.relationships:
                context += "\n**Relationships:**\n"
                for rel in table.relationships:
                    context += f"- {rel}\n"
            
            context += "\n"
        
        return context
    
