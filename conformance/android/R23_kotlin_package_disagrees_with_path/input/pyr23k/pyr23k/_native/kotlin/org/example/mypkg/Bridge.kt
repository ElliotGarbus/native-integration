// The path says `org.example.mypkg`, which `pyr23k` owns. This says otherwise,
// and `kotlinc` compiles it without complaint.
package org.other

class Bridge {
    fun start(): Boolean = true
}
