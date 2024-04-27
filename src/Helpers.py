import datetime
import logging
from lxml import etree
import polib
import re

# TODO: this is also in main file
version = "0.6.7"

labels = [
    'beginLetter',
    'beginLetterLabel',
    'description',
    'fixedName',
    'gerund',
    'gerundLabel',
    'helpText',
    'ingestCommandString',
    'ingestReportString',
    'inspectLine',
    'label',
    'labelShort',
    'letterLabel',
    'letterText',
    'pawnLabel',
    'pawnsPlural',
    'rulesStrings',         # hard one
    'recoveryMessage',
    'reportString',
    'skillLabel',
    'text',
    'useLabel',
    'verb',
]

defNames = [
    'defName',
    'DefName',  # Some DefNames with first uppercase letter
]

# TODO: this is a private method
def generate_definj_xml_tag(string):
    """Create XML tag for InjectDefs"""
    string = re.sub(r'/', '.', string)
    string = re.sub(r'\.li\.', '.0.', string)
    string = re.sub(r'\.li$', '.0', string)
    match = re.search(r'\.li\[(\d+)\]', string)
    if match:
        string = re.sub(r'\.li\[\d+\]', "." + str(int(match.group(1)) - 1), string)

    return string

def create_logger(log_level_string):
    log_format = '%(levelname)s: %(message)s' 
    log_level = getattr(logging, str.upper(log_level_string))

    logging.basicConfig(
        format=log_format,
        level=log_level,
        filename='RimTranslate.log' # TODO: change log name to not be too close to runtime name
    )

    # TODO: set streamhandler to not output to stderr by default
    #       https://docs.python.org/3/library/logging.handlers.html#logging.StreamHandler
    console = logging.StreamHandler()
    console.setLevel(log_level)
    console.setFormatter(logging.Formatter(log_format))

    logger = logging.getLogger('main')
    logger.addHandler(console)
    return logger

def create_pot_file_from_keyed(filename, source_dir, compendium, compendium_mode=False):
    """Create compendium from keyed or already created definj XML files"""
    parser = etree.XMLParser(remove_comments=True)
    if compendium:
        basefile = 'compendium'
    else:
        basefile = filename.split(source_dir, 1)[1]

    po_file = polib.POFile()
    po_file.metadata = {
        'Project-Id-Version': '1.0',
        'Report-Msgid-Bugs-To': 'you@example.com',
        'POT-Creation-Date': str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M")),
        'PO-Revision-Date': str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M")),
        'Last-Translator': 'Some Translator <yourname@example.com>',
        'Language-Team': 'English <yourteam@example.com>',
        'MIME-Version': '1.0',
        'Content-Type': 'text/plain; charset=utf-8',
        'Content-Transfer-Encoding': '8bit',
    }
    po_file.metadata_is_fuzzy = 1
    doc = etree.parse(filename, parser)
    for languageData in doc.xpath('//LanguageData'):
        for element in languageData:
            entry = polib.POEntry(
                msgctxt=element.tag,
                msgid=element.text,
                occurrences=[(basefile, str(element.sourceline))]
            )
            if compendium_mode:
                entry.msgstr = element.text
            po_file.append(entry)

    return po_file


def create_pot_file_from_def(filename, source_dir):
    """Create POT file (only source strings exists) from given filename"""
    doc = etree.parse(filename)
    po_file = polib.POFile()
    basefile = filename.split(source_dir, 1)[1]
    po_file.metadata = {
        'Project-Id-Version': '1.0',
        'Report-Msgid-Bugs-To': 'you@example.com',
        'POT-Creation-Date': str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M")),
        'PO-Revision-Date': str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M")),
        'Last-Translator': 'Some Translator <yourname@example.com>',
        'Language-Team': 'English <yourteam@example.com>',
        'MIME-Version': '1.0',
        'Content-Type': 'text/plain; charset=utf-8',
        'Content-Transfer-Encoding': '8bit',
    }
    po_file.metadata_is_fuzzy = 1

    for defName in defNames:
        for defName_node in doc.findall(".//" + defName):
            if defName_node is not None:
                parent = defName_node.getparent()
                logging.debug("Found defName '%s' (%s)" % (defName_node.text, doc.getpath(parent)))
                for label in labels:
                    parent = defName_node.getparent()
                    logging.debug("Checking label %s" % label)
                    label_nodes = parent.findall(".//" + label)
                    for label_node in label_nodes:
                        logging.debug("Found Label '%s' (%s)" % (label, doc.getpath(label_node)))
                        if len(label_node):
                            logging.debug("Element has children")
                            for child_node in label_node:
                                if child_node.tag is not etree.Comment:
                                    path_label = doc.getpath(child_node).split(doc.getpath(parent), 1)[1]
                                    path_label = generate_definj_xml_tag(path_label)

                                    logging.debug("msgctxt: " + defName_node.text + path_label)
                                    entry = polib.POEntry(
                                        msgctxt=defName_node.text + path_label,
                                        msgid=child_node.text,
                                        occurrences=[(basefile, str(label_node.sourceline))]
                                    )
                                    po_file.append(entry)
                        else:
                            # Generate string for parenting
                            path_label = doc.getpath(label_node).split(doc.getpath(parent), 1)[1]
                            path_label = generate_definj_xml_tag(path_label)

                            logging.debug("msgctxt: " + defName_node.text + path_label)

                            if not label_node.text:
                                logging.warning(path_label + " has 'None' message!")
                            else:
                                entry = polib.POEntry(
                                    msgctxt=defName_node.text + path_label,
                                    msgid=label_node.text,
                                    occurrences=[(basefile, str(label_node.sourceline))]
                                )
                                po_file.append(entry)
    # sort by line in source file
    po_file.sort(key=lambda x: int(x.occurrences[0][1]))

    return po_file


def create_languagedata_xml_file(po_file):
    languagedata = etree.Element('LanguageData')
    languagedata.addprevious(etree.Comment(' This file autogenerated with RimTranslate.py v%s ' % version))
    languagedata.addprevious(etree.Comment(' https://github.com/winterheart/RimTranslate/ '))
    languagedata.addprevious(etree.Comment(' Don\'t edit this file manually, edit PO file and regenerate this file! '))
    xml = etree.ElementTree(languagedata)
    po = polib.pofile(po_file)
    for po_entry in po:
        if (po_entry.msgstr != "") and ('fuzzy' not in po_entry.flags):
            entry = etree.SubElement(languagedata, po_entry.msgctxt)
            entry.text = str(po_entry.msgstr)
    # Hack - silly lxml cannot write native unicode strings
    xml_file = etree.tostring(xml, pretty_print=True, xml_declaration=True, encoding='utf-8').decode('utf-8')
    return xml_file
