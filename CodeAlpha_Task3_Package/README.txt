CODEALPHA TASK 3 - SENSOR-BASED CONVEYOR BELT AUTOMATION
Student: Meet Agrawal | B.Tech. Robotics & Artificial Intelligence | Ramdeobaba University, Nagpur | Roll No. 17

CONTENTS
Report/   Task3_Conveyor_Automation_Report.pdf (submit) and .docx (editable), 3 pages
Diagrams/ Circuit_Diagram, Block_Diagram, Flowchart, State_Diagram (.png and editable .svg)
          Flowchart.dot, State_Diagram.dot, Block_Diagram.dot (Graphviz sources), draw_circuit.py (circuit source)
Design/   Conveyor_Control/Conveyor_Control.ino  (Arduino Uno sketch)
Test/     test_conveyor.cpp + Arduino.h (host test harness), test_results.txt (22/22 checks), scenario1.csv, scenario1_timeline.png

RE-RUN THE TESTS (needs g++):   cd Test && g++ -std=c++17 -I. -o test_conveyor test_conveyor.cpp && ./test_conveyor

NOTE
Tested in simulation only (the real sketch against a simulated belt). The circuit has not been built; check component
ratings against the actual motor and sensors. The emergency stop must cut motor power in hardware (S1a), not only in software.
