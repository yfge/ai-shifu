// import { MDXEditor } from '@mdxeditor/editor';
import MDXEditor from '@/components/md-editor';
import Markdown from '@/components/markdown'
import TextEditor from '@/components/text-editor';
// import { ALL_PLUGINS } from '@/components/md-editor';
// import { Textarea } from '../ui/textarea';
// import MarkdownEditor from '@/components/markdown-editor'

interface SolideContnetProps {
    content: string;
    profiles: string[];
}

interface SolideContnet {

    isEdit: boolean;
    properties: SolideContnetProps;
    onChange: (properties: SolideContnetProps) => void;
}

export default function SolidContent(props: SolideContnet) {
    if (props.properties.prompt) {
        props.properties.content = props.properties.prompt;
        delete props.properties.prompt;
        delete props.properties.model;
        delete props.properties.temprature;
        delete props.properties.other_conf;
    }

    return (
        <TextEditor
            content={props.properties.content}
            profiles={props.properties.profiles}
            onChange={(value) => {
                props.onChange({ ...props.properties, content: value })
            }}
        />

    )
  
}
