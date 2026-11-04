from __future__ import annotations

import os
import tempfile
import unittest

from bpmndiff.parsers import ParseError, load_model


XPDL = """<?xml version="1.0" encoding="utf-8"?>
<Package xmlns="http://www.wfmc.org/2009/XPDL2.2" Id="pkg" Name="Package">
  <Pools>
    <Pool Id="pool" Name="Cashier pool" Process="proc" BoundaryVisible="true">
      <Lanes>
        <Lane Id="lane1" Name="Cashier" ParentPool="pool">
          <NodeGraphicsInfos>
            <NodeGraphicsInfo Height="100" Width="400">
              <Coordinates XCoordinate="0" YCoordinate="0" />
            </NodeGraphicsInfo>
          </NodeGraphicsInfos>
        </Lane>
      </Lanes>
    </Pool>
  </Pools>
  <WorkflowProcesses>
    <WorkflowProcess Id="proc" Name="Down payment">
      <Activities>
        <Activity Id="start" Name="">
          <Event><StartEvent Trigger="None" /></Event>
          <NodeGraphicsInfos><NodeGraphicsInfo Height="30" Width="30"><Coordinates XCoordinate="10" YCoordinate="20" /></NodeGraphicsInfo></NodeGraphicsInfos>
        </Activity>
        <Activity Id="task1" Name="Enters down payment information">
          <Implementation><Task /></Implementation>
          <NodeGraphicsInfos><NodeGraphicsInfo Height="30" Width="90"><Coordinates XCoordinate="80" YCoordinate="20" /></NodeGraphicsInfo></NodeGraphicsInfos>
        </Activity>
        <Activity Id="gw" Name="">
          <Route />
          <NodeGraphicsInfos><NodeGraphicsInfo Height="40" Width="40"><Coordinates XCoordinate="200" YCoordinate="20" /></NodeGraphicsInfo></NodeGraphicsInfos>
        </Activity>
        <Activity Id="task2" Name="Saves the information">
          <Implementation><Task /></Implementation>
          <NodeGraphicsInfos><NodeGraphicsInfo Height="30" Width="90"><Coordinates XCoordinate="280" YCoordinate="20" /></NodeGraphicsInfo></NodeGraphicsInfos>
        </Activity>
        <Activity Id="end" Name="">
          <Event><EndEvent Result="None" /></Event>
          <NodeGraphicsInfos><NodeGraphicsInfo Height="30" Width="30"><Coordinates XCoordinate="400" YCoordinate="20" /></NodeGraphicsInfo></NodeGraphicsInfos>
        </Activity>
      </Activities>
      <Transitions>
        <Transition Id="t0" From="start" To="task1"><Condition /></Transition>
        <Transition Id="t1" From="task1" To="gw"><Condition /></Transition>
        <Transition Id="t2" From="gw" To="task2"><Condition Type="CONDITION"><Expression /></Condition></Transition>
        <Transition Id="t3" From="task2" To="end"><Condition /></Transition>
      </Transitions>
    </WorkflowProcess>
  </WorkflowProcesses>
</Package>
"""

BPMN = """<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL" id="defs">
  <collaboration id="collab">
    <participant id="p1" name="Clinic pool" processRef="proc" />
  </collaboration>
  <process id="proc" name="BPMN process">
    <laneSet id="ls">
      <lane id="lane" name="Front office">
        <flowNodeRef>start</flowNodeRef>
        <flowNodeRef>task</flowNodeRef>
      </lane>
    </laneSet>
    <startEvent id="start" name="Request received" />
    <task id="task" name="Check request" />
    <exclusiveGateway id="gw" name="" />
    <task id="task2" name="Save request" />
    <endEvent id="end" name="" />
    <sequenceFlow id="f0" sourceRef="start" targetRef="task" />
    <sequenceFlow id="f1" sourceRef="task" targetRef="gw" />
    <sequenceFlow id="f2" sourceRef="gw" targetRef="task2" />
    <sequenceFlow id="f3" sourceRef="task2" targetRef="end" />
  </process>
</definitions>
"""


class ParserTests(unittest.TestCase):
    def _write(self, suffix: str, content: str) -> str:
        handle, path = tempfile.mkstemp(suffix=suffix)
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(content)
        self.addCleanup(os.unlink, path)
        return path

    def test_xpdl_parsing(self):
        model = load_model(self._write(".xpdl", XPDL))
        self.assertEqual(model.name, "Down payment")
        self.assertEqual(model.pool, "Cashier pool")
        self.assertEqual(model.fmt, "xpdl")
        self.assertEqual(model.stats()["nodes"], 5)
        self.assertEqual(model.nodes["gw"].kind, "xor")
        self.assertEqual(model.nodes["task1"].lane, "Cashier")
        self.assertEqual(len(model.edges), 4)

    def test_bpmn_parsing(self):
        model = load_model(self._write(".bpmn", BPMN))
        self.assertEqual(model.name, "BPMN process")
        self.assertEqual(model.pool, "Clinic pool")
        self.assertEqual(model.fmt, "bpmn")
        self.assertEqual(model.nodes["gw"].kind, "xor")
        self.assertEqual(model.nodes["task"].lane, "Front office")
        self.assertEqual(model.start_nodes(), ["start"])
        self.assertEqual(model.end_nodes(), ["end"])

    def test_unsupported_root(self):
        path = self._write(".xml", "<root><child /></root>")
        with self.assertRaises(ParseError):
            load_model(path)

    def test_missing_file(self):
        with self.assertRaises(ParseError):
            load_model("/definitely/not/here.xpdl")


if __name__ == "__main__":
    unittest.main()
